# Phase E2 — Module B (AIBOM import/export) report

Self-assessed. Fabrication of results is prohibited; anything not run is reported
as not run. This module is independent of the Part B-D session, the holdout, and
GATE E2 — it touches none of them.

Reference: `SPEC.md` **Module B** (B.1–B.6), fixed before implementation.
Decisions: `DECISIONS.md` D-42..D-44.

## 1. Module map

| file | lines | role |
|---|---|---|
| `src/releaseseal/bom/__init__.py` | 14 | public surface (`import_bom`, `verify_bom`, `export_bom`, `artifacts_from_snapshot`) |
| `src/releaseseal/bom/facts.py` | 309 | BOM document → `bomfacts/1` (CycloneDX 1.5/1.6/1.7, SPDX 3.0 AI); format detection; `ignored` / `unmapped` counting |
| `src/releaseseal/bom/verify_bom.py` | 195 | `bomfacts/1` + artifact set → `bom-result/1` (B1 findings + unverifiable); `artifacts_from_snapshot` |
| `src/releaseseal/bom/export.py` | 133 | evidence pack (+ optional snapshot) → CycloneDX 1.6 document |
| `bench/bom_cases.py` | 221 | 24-case mini-bench (`bom-manifest/1`) + exact-match scorer |
| CLI (`src/releaseseal/cli.py`) | — | `bom import` / `bom export` subcommands |
| `fixtures/bom/*.json` | — | 5 BOM documents (CycloneDX 1.5/1.6/1.7, SPDX ×2) + 3 paired artifact snapshots |
| `tests/test_bom_*.py` | — | import, verify, export, bench, CLI (42 tests) |

## 2. Decidable-check table

All findings use the `finding/1` shape with `check = "B1"`; none is `info`, so B1
findings count like V1–V7 (non-heuristic, gate-weight — though Module B has no
gate). Each check was tested positive and negative (`tests/test_bom_verify.py`).

| code | severity | fires when | needs artifacts? | +/- tested |
|---|---|---|---|---|
| `bom_hash_mismatch` | high | same-alg hash differs from the paired artifact file (matched by path, then basename; case-insensitive) | yes | ✓ / ✓ |
| `bom_license_mismatch` | medium | component declared license ≠ paired snapshot's declared license (case-insensitive) | yes | ✓ / ✓ |
| `bom_dangling_ref` | medium | a `depends_on` edge names a bom-ref absent from the document | **no** (pure document) | ✓ / ✓ |
| `bom_undeclared_artifact` | medium | a weight/data file in the artifact set no component accounts for | yes | ✓ / ✓ |

Weight/data extensions (B.2): weights `.safetensors .bin .gguf .onnx .pt .pth .h5
.msgpack .tflite .npz`; data `.jsonl .csv .parquet .arrow .tfrecord`. Non-weight
files (README, config, `.gitattributes`) never raise `bom_undeclared_artifact`
(tested).

### Importers

- **CycloneDX 1.5 / 1.6 / 1.7** — `metadata.component` + `components[]`; model /
  dataset / other classification; licenses (id|name|expression), hashes
  (alg→content verbatim), `dependencies[]` edges. Non-model/dataset components are
  kind `"other"` **and** counted in `ignored` by raw type (e.g. `{"file":2,
  "library":1}`). Spec version drives `source_format`.
- **SPDX 3.0 AI (JSON-LD)** — `@graph` `software_Package` elements; `spdxId→bom_ref`,
  `versionInfo→version`, `hasConcludedLicense`→(else)`hasDeclaredLicense`,
  `verifiedUsing` Hash (`sha256`→`SHA-256` normalized so hashes compare across
  formats), `dependsOn` relationships. Model vs dataset from profile/type markers
  (`typeOfModel`/`AIPackage` vs `datasetType`/`DatasetPackage`). An element that
  cannot be mapped to a package is counted in `unmapped`, never guessed (tested:
  the `simplelicensing_LicenseExpression` element in
  `fixtures/bom/spdx-3.0-ai-with-unmapped.json` → `unmapped: 1`, 1 component).

## 3. Mini-bench result (regression suite, NOT a gate)

Run: `python bench/bom_cases.py`

```
ReleaseSeal Module B mini-bench
  cases: 24  cases_sha256: 312e000e29e90f70...
  composition: {'hash_mismatch': 4, 'license_mismatch': 4, 'dangling_ref': 4,
                'undeclared_artifact': 4, 'clean': 5, 'clean_unverifiable': 1,
                'spdx_clean': 1, 'spdx_hash_mismatch': 1}
  exact-match: 24/24  (PASS)
```

- `cases_sha256` (full): `312e000e29e90f70e385a97d20e561ef227b71b362ebda95054b3b2b5c798433`.
- Composition = the B.4 table: hash mismatch ×4, license mismatch ×4, dangling ref
  ×4, undeclared artifact ×4, clean ×6 (5 fully-paired + 1 whose claims are simply
  unverifiable → non-empty `unverifiable`, `[]` findings), SPDX-import ×2 (1 clean,
  1 hash mismatch).
- Scorer is **exact**: the set of B1-producing cases equals the set with non-empty
  `expected`; every clean case yields zero B1 findings. **24/24.**
- Regeneration is byte-identical (tested: `test_bench_regeneration_byte_identical`).
- Marker discipline (tested): `expected` is a subset of `{"B1"}` for defect cases,
  `[]` for clean — class ids only, never codes, never severities.

## 4. Unverifiable-count design note

The decidable-subset rule (extension design §2/§7) is enforced by making
**unverifiable a first-class, counted outcome**, never a silent pass and never a
finding:

- For every component, its hash claim(s) and its license claim are *verifiable*
  only when the matching evidence is in the paired artifact set. Otherwise exactly
  one `{component, claim, reason}` entry is emitted — `reason ∈ {"no artifact set
  provided", "no matching artifact file", "no declared license in artifact set",
  "no comparable hash in artifact set"}`.
- A component whose hash **is** checked (artifact match present) never also appears
  as `unverifiable` for `hash` (tested: `test_verified_hash_not_also_unverifiable`).
- A component with no declared hashes contributes no hash claim at all (tested).
- `bom_dangling_ref` is the one check that needs no artifacts — it is pure document
  consistency — so it runs even when everything else is unverifiable (tested;
  `bom import` with no `--artifacts` yields only dangling findings).
- `bom-result/1.counts` surfaces the accounting: `unverifiable`,
  `unverifiable_by_claim`, `by_code`, `components` (model/dataset/other),
  `ignored`, `unmapped`. Example (SPDX fixture, no artifacts): `unverifiable: 3`
  (`license: 2, hash: 1`), `findings: 0`.

This is the honest answer to "no wild AIBOM population" (extension design §2): a
BOM whose described artifacts are not in hand is **measured as unverifiable**, not
passed.

## 5. Round-trip (export → import)

`import_bom(export_bom(pack, snapshot))` recovers the same component set —
`(name, kind, hashes)` triples — the export wrote: the release (kind
model/dataset) plus each emitted file component (kind `"other"`, since CycloneDX
`type:"file"` is not a model/dataset type). Tested for a model pack (`pack/1`) and
a dataset pack (`pack/2`), and idempotent. The snapshot digest travels as a
property, never as a component hash (D-42). Export is byte-deterministic (tested).

## 6. Determinism / cost / offline

- Every Module B output (`bomfacts/1`, `bom-result/1`, the exported document, the
  mini-bench manifest) is canonical-serialized (D-09) and byte-identical on
  re-run (tested in each of the 5 test files).
- `$0`, stdlib only, no network. The importers read JSON already in hand; nothing
  fetches. Tests never touch the network.

## 7. Test result

```
python -m pytest -q
183 passed
```

141 pre-existing (model + dataset suites, unmodified) + 42 new Module B tests.
Both importers are exercised from `fixtures/bom/`; each decidable check is tested
positive and negative; unverifiable accounting, export round-trip, mini-bench
exact-match, and determinism all covered.

## 8. Deviations (DECISIONS ids)

- **D-42** — `export_bom` takes an **optional** `--snapshot`. The design/prompt CLI
  (`releaseseal bom export <pack.json>`) names only the pack, but a pack references
  its snapshot by hash and does not embed the file inventory, so file components
  and the declared license are unavailable from the pack alone. Pack-only export
  emits the release component + findings summary (valid, round-trips to the
  release); `--snapshot` adds file components (hashes where known) and the license.
  The snapshot digest is carried as `properties["releaseseal:snapshot_sha256"]`,
  **not** as a component `SHA-256` hash (it is the digest of the snapshot JSON, not
  of any file — carrying it as a file hash would be a false claim).
- **D-43** — Facts carry `"other"`-kind components in `components[]` **and** a
  separate `ignored` count. The prompt says "record other types as
  ignored-with-count", and the facts shape lists `kind: "…"|"other"`. Reconciled:
  other-typed CycloneDX components are transcribed as kind `"other"` (so they
  round-trip and are visible) and additionally counted in `ignored` by raw type.
  SPDX shapes that map to no package are a distinct outcome: `unmapped` (a count;
  never a guessed component).
- **D-44** — SPDX `sha256` hash values are normalized to the CycloneDX algorithm
  spelling (`"SHA-256"`) on import, so a hash imported from SPDX compares correctly
  against a CycloneDX hash and against a snapshot's `sha256`. Hash *content* is
  never altered; only the algorithm label is canonicalized.

## 9. Scope held (Module B hard rules)

- Decidable subset only. No semantic judgement (is this license *really*
  compatible, is this dataset *really* the one described) — such claims are
  `unverifiable`, never a finding and never a pass.
- Not a gate: the mini-bench is a regression check; no holdout.
- Non-certification discipline carries into export: findings travel as consistency
  properties, never a compliance attestation.
