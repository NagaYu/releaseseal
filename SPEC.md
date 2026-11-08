# ReleaseSeal — SPEC (Phase 1)

Public name **ReleaseSeal** (was codename "ModelPass"; see DECISIONS.md D-01 / D-13).
Derived from `modelpass-design.md` (authoritative; design-era filename kept). This SPEC fixes the concrete shapes the design describes so the
implementation and tests have one reference. Section numbers here are local.

## 1. Product definition

Given a model release — a Hugging Face repo at a pinned revision, or a local
release directory — ReleaseSeal checks whether the release's **documentation and
declared metadata agree with its artifacts and with each other**, and emits a
schema-versioned, hash-chained **evidence pack** (JSON + Markdown report)
verifiable offline.

It verifies *consistency and completeness of evidence*. It never certifies legal
compliance. Wording discipline (design §1, §9): the output is an **evidence
pack**, never a "certificate"; findings describe *inconsistencies between
documentation and artifacts*, never a legal verdict.

Pipeline:

```
release ──adapter──▶ snapshot JSON ──verify (pure)──▶ findings JSON ──pack──▶ evidence pack ──report──▶ Markdown
                                        ▲ rule packs (data, versioned)
```

The core (`snapshot JSON → findings JSON`) is a deterministic pure function. No
network, no servers, no paid APIs at verify time.

## 2. Snapshot schema (`schema_version: "snapshot/1"`)

A snapshot is JSON. Top-level fields:

| field | type | notes |
|---|---|---|
| `schema_version` | str | `"snapshot/1"` |
| `captured_at` | str | ISO-8601 date/datetime; capture time |
| `source` | object | release identity (below) |
| `files` | array | one file record each (below) |
| `card` | object | parsed model card (below) |
| `config` | object/null | `config.json` contents (verbatim subset) |
| `generation_config` | object/null | `generation_config.json` |
| `tokenizer_config` | object/null | `tokenizer_config.json` |
| `chat_template` | str/null | chat template string if present |
| `safetensors_index` | object/null | `{metadata:{total_size:int?}, weight_map:{tensor:file}}` or header facts |
| `model_index` | array/null | HF `model-index` (eval results) parsed from card |
| `result_files` | object | map `path -> parsed JSON` for eval result files in repo |
| `snapshot_sha256` | str/null | canonical content hash (D-09); filled by writer |

`source` object:

| field | type | notes |
|---|---|---|
| `adapter` | str | `"hf"` or `"local"` |
| `repo_id` | str/null | e.g. `"org/model"` (hf) |
| `revision` | str/null | commit sha / tag (hf) |
| `path` | str/null | directory (local) |

`files[]` record:

| field | type | notes |
|---|---|---|
| `path` | str | repo-relative path |
| `size` | int/null | bytes; null if unknown |
| `sha256` | str/null | content hash; for large files this is the **source-provided LFS SHA-256** (hf) or a streamed hash (local) |
| `hash_source` | str | `"lfs"`, `"streamed"`, or `"none"` |

`card` object (parsed from `README.md`):

| field | type | notes |
|---|---|---|
| `yaml` | object | card front-matter (license, base_model, tags, model-index, …) |
| `prose` | str | card body text (markdown minus front-matter) |
| `claims` | object | extracted structured claims (below) |

`card.claims` (extracted, best-effort, deterministic):

| field | type | notes |
|---|---|---|
| `param_count` | int/null | claimed parameter count (from YAML or prose like "7B") |
| `param_count_text` | str/null | the raw text the count came from |
| `context_length` | int/null | claimed context/max position |
| `architecture` | str/null | claimed architecture family |
| `license` | str/null | declared license id (SPDX-ish) |
| `base_model` | array | declared base model ids (lineage parents) |
| `base_model_relation` | str/null | `adapter`/`merge`/`quantized`/`finetune`/null |
| `eval_claims` | array | `{benchmark, metric, value, source}` headline eval claims found in prose |

### 2.1 Lineage in the snapshot

For a release with ancestors, the snapshot MAY embed the ancestors it can see as
`card.claims.base_model` (ids) plus a `lineage` map (id → `{license, requires_notice}`)
when the adapter resolved them. The `local` and synthetic adapters provide
`lineage` explicitly; the `hf` adapter fills what the ancestor cards declare.

`lineage` map value: `{"license": str|null, "requires_notice": bool|null,
"notice_present_in_ancestor": bool|null}`.

## 3. Verification classes

Deterministic V1–V7; V8 is signal-only. Each check reads the snapshot (+ active
rule packs + context) and returns zero or more findings.

- **V1 Artifact–record mismatch** — files the card/config reference but absent;
  weight files present but undocumented; a `files[]` `sha256` that disagrees with
  a digest recorded elsewhere (e.g. safetensors `weight_map` referencing a file
  not in `files`, or an index `total_size` inconsistent with file sizes).
- **V2 Architecture & scale claims** — `card.claims.param_count` vs the config
  parameter estimate (D-02, ±20%); claimed `architecture`/`context_length` vs
  `config` (`model_type`, `max_position_embeddings`); `base_model_relation`
  inconsistent with artifacts (e.g. relation `adapter` but full weight shards and
  no adapter files; relation `quantized` but no quantization config).
- **V3 License lineage** — walk `base_model` to roots (Phase 2: the `hf` adapter
  resolves the chain **recursively**, depth cap 8 + cycle guard, flattening all
  ancestors into the snapshot `lineage` map — D-14); the declared license must be
  permitted by every ancestor's license per `license-terms-v1`; missing
  NOTICE/attribution artifact where an ancestor requires it. Unknown/unreachable
  ancestor license → `license_unknown` (low), never an inferred-compatible
  verdict (D-07). Ancestor findings carry the ancestor id in `subject`.
- **V4 Mandatory documentation gaps** — Annex XI / Annex XII field completeness
  per active rule pack (incl. training-content summary & copyright-policy
  presence for providers); Code-of-Practice Model Documentation Form as a second
  pack. Each gap cites the rule id and its regulatory source.
- **V5 Staleness / revision drift** — card/model-index names a different
  revision than `source.revision`; `as-of` dates before the context's `as_of_now`
  (D-10); eval result whose recorded source names another checkpoint.
- **V6 Evaluation claim inconsistency** — `model_index` numbers vs values in
  `result_files`; same benchmark with different values in different card
  sections; headline eval claim in prose with no structured source anywhere.
- **V7 Release completeness** — tokenizer files, chat template, generation
  config and safetensors index internally consistent (e.g. `weight_map` tensors
  all map to listed files; a chat template referenced by tokenizer_config exists;
  generation_config references no absent file). The release can be loaded as
  documented.
- **V8 Undeclared derivation (signal only)** — config fingerprint (D-08) matches
  a known base while `base_model` empty. Always `heuristic:true`, `info`, never a
  gate input.

### 3.1 Severity & gates

Severity order `info < low < medium < high` (D-03). Gate/CI rollups count only
V1–V7 findings; V8 (`heuristic:true`) is always excluded.

## 4. Finding schema (`finding/1`)

```json
{
  "check": "V3",
  "code": "license_incompatible",
  "severity": "high",
  "heuristic": false,
  "message": "Declared license 'apache-2.0' not permitted by ancestor 'meta-llama/Llama-3-8B' (llama-3-community).",
  "evidence": {
    "file": "README.md",
    "field": "license",
    "expected": "a license permitted by llama-3-community",
    "actual": "apache-2.0"
  }
}
```

- `check`: `"V1".."V8"`.
- `code`: stable short slug (snake_case) for the finding type.
- `severity`: `info|low|medium|high`.
- `heuristic`: bool (`true` only for V8).
- `evidence`: `{file, field, expected, actual}`, any field nullable; `expected`/
  `actual` are strings or null (D-04).
- `subject` (optional, Phase 2): a structured id the finding is *about* — for V3,
  the lineage ancestor id. Nullable; consumers may ignore it. Used by the
  lineage-walk-accuracy metric to compare detected vs planted violating ancestors.

Findings output: `{"schema_version":"findings/1","rule_packs":{...},
"findings":[...]}` where `rule_packs` records the versions actually used.

## 5. Rule packs (data; versioned independently)

Each pack is a JSON file in `rules/packs/` with `{pack_id, version, source,
...}`. A finding records the pack versions used. Packs:

- **`hub-metadata-v1`** — HF card metadata: required/recommended front-matter
  fields and their format (used by V4 `hub` profile, and format checks).
- **`gpai-eu-v1`** — EU AI Act Annex XI / Annex XII item lists and the GPAI Code
  of Practice Model Documentation Form items. Every item carries its regulatory
  `source` (article/annex reference). Used by V4.
- **`license-terms-v1`** — license compatibility table: per license, which
  licenses a derivative may declare, whether attribution/NOTICE is required, and
  commercial-use restriction flags. Unknown license → judged "undeterminable".
- **`fingerprints-v1`** — (V8 data) fingerprint hash → known base id. Phase 2
  (`v1.1.0`) seeds `known_bases` from popular open base-model configs so V8 can
  fire on real data.

## 5b. Bench dev_ext + Part B (Phase 2)

- **dev_ext** (`bench-manifest-ext/1`, D-15): an *additive*, separately-seeded
  manifest of multi-level lineage cases (grandparent violation, unknown
  intermediate, deep attribution, multi-parent merge, deep clean). The frozen
  120-case dev split is unchanged. Each case adds `lineage_truth`: the set of
  ancestor ids that are genuine violations (incompatible or attribution-missing;
  `license_unknown` is **not** a violation).
- **lineage-walk accuracy** (design §5): fraction of lineage cases whose detected
  violating-ancestor set (from V3 findings' `subject`, codes
  `license_incompatible`/`attribution_missing`) equals `lineage_truth`.
- **Part B** (`partb-models/1`): a frozen list `bench/partb/models.json` of ~40
  real public models with pinned revisions, snapshotted live via the `hf` adapter
  (metadata + small files only; no weights), verified with the frozen packs.
  Evidence packs + snapshots saved under `audit/partb/`; `summary.json` records
  per-class occurrence rate, code totals, and every model's result (no cherry-
  picking). Run with `bench/partb/run_partb.py` (smoke path; not a test).

Pack version is independent of the code version and appears in every pack's
`version` field and in each finding set's `rule_packs`.

## 6. Bench — Part A (synthetic)

### 6.1 Generator

Builds small synthetic releases (metadata + tiny stand-in artifacts, **no real
weights**) with planted discrepancies across V1–V7, plus clean releases
including near-miss cleans (unusual-but-valid license; a merge with correct
paperwork). Seeded: same `seed` → identical bytes (tested).

Dev split: **120 cases** — V1–V7 each 12 (=84) + 36 clean. Emits a `manifest`.

### 6.2 Case manifest schema (value types fixed — D-06)

`manifest.json`:

| field | type | notes |
|---|---|---|
| `schema_version` | str | `"bench-manifest/1"` |
| `seed` | int | generator seed |
| `cases_sha256` | str (64 hex) | hash over the ordered serialized cases |
| `composition` | object | map `"V1".."V7"` → int and `"clean"` → int |
| `cases` | array | case records (below) |

Case record:

| field | type | constraint |
|---|---|---|
| `id` | str | `"case-%04d"` |
| `kind` | str | one of `"V1","V2","V3","V4","V5","V6","V7","clean"` |
| `expected` | array of str | **markers**: subset of `{"V1".."V7"}`; `[]` for clean (D-06) |
| `snapshot` | object | a full snapshot (schema `snapshot/1`) |

Markers are the check-class ids only — never free text, never severities.
A planted `Vk` case has `expected` containing `"Vk"` (and nothing the case does
not actually plant). A `clean` case has `expected: []` and must raise no V1–V7
finding.

### 6.3 Scorer

Given the manifest + the verifier, compute deterministically:

- **per-class recall** for V1–V7: of cases whose `expected` contains `Vk`, the
  fraction for which the verifier emitted ≥1 `Vk` finding.
- **clean FP rate**: of `clean` cases, the fraction that got ≥1 V1–V7 finding.

V8 findings are ignored by the scorer (never gate-counted).

## 7. Evidence pack (`schema_version: "pack/1"`) & verify-pack

A pack is an ordered record list with a hash chain (D-05):

```
records[0] = {"type":"header", "pack_schema":"pack/1", "app":<APP_CODENAME>,
              "created_at":..., "rule_packs":{...}, "prev":"00..0"}
records[1] = {"type":"snapshot_ref", "snapshot_sha256":..., "source":{...}, "prev":sha256(records[0])}
records[k] = {"type":"finding", "finding":{...}, "prev":sha256(records[k-1])}
chain_tip  = sha256(records[-1])
```

`verify-pack` recomputes every `prev` and the tip and (if the snapshot is
supplied) rechecks `snapshot_sha256`, fully offline. Any edit to any record
breaks the chain from that point on.

Markdown report is generated from the pack (grouped by check and severity,
evidence pointers inline, rule-pack versions footed, with the non-certification
disclaimer).

## 8. CLI

Thin callers over the core:

- `releaseseal snapshot --local <dir> -o snap.json` / `--hf <repo> [--revision r]`
- `releaseseal verify snap.json [-o findings.json] [--as-of DATE]`
- `releaseseal pack snap.json [-o pack.json] [--report report.md]`
- `releaseseal verify-pack pack.json [--snapshot snap.json]`
- `releaseseal bench generate [--seed N] [--n 120] -o <dir>`
- `releaseseal bench score --manifest <dir>/manifest.json`

## 9. GATE 1

PASS iff, on the dev synthetic split: **per-class recall ≥ 0.90 for every one of
V1–V7**, **clean false-positive rate ≤ 5%**, and the full test suite is green.
V8 is excluded from the gate entirely. Self-assessed in `reports/phase1.md` with
the measured numbers; fabrication of results is prohibited.

## 9b. GATE 2 (Phase 2)

PASS iff, on the sealed independent **holdout** (scored once with the frozen
verifier): **per-class recall ≥ 0.85 for every V1–V7** and **clean FP ≤ 5%**. V8
excluded. If no holdout is delivered, GATE 2 is **judgment-pending** and Part B
is reported in full. Self-assessed in `reports/phase2.md`; predictions are
pre-registered in `reports/phase2-predictions.md` before Part B / holdout.

## 10. Hard rules (from design §9)

- Verifies consistency only; never claims to verify truth of training-data or
  capability claims; never issues legal compliance certification; no
  "certificate" wording anywhere.
- No full weight downloads (metadata + small files only). $0 spend. Local-first.
  Tests never touch the network (hf adapter tested against recorded fixtures).
- V8 is a labelled heuristic signal, never a gate input.
