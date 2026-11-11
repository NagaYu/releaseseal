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

---

# Extension E1 — dataset snapshots and W classes

This section is the single reference for the dataset-verification core (extension
design §3, Module D). It fixes every concrete shape **before implementation**.
Where this section and the extension design disagree, this section's pinned
values win (the Phase-E1 authoring prompt's rule); each such choice is recorded
in DECISIONS.md (D-27..D-36). Model-side shapes (§1–§10 above) are unchanged; the
core dispatches on `schema_version` (`snapshot/1` → V-checks, `dsnapshot/1` →
W-checks) and model evidence packs remain `pack/1`, byte-for-byte as before.

## E1.1 Dataset snapshot schema (`schema_version: "dsnapshot/1"`)

Top-level fields:

| field | type | notes |
|---|---|---|
| `schema_version` | str | `"dsnapshot/1"` |
| `captured_at` | str | ISO-8601 |
| `source` | object | `{adapter, repo_id, revision, path}`; `adapter ∈ {"hf_dataset","local_dataset"}`; all keys present, null where N/A (same nullability as §2) |
| `files` | array | one record each: `{path, size:int|null, sha256:str|null, hash_source}` (identical to §2 `files[]`) |
| `card` | object | `{yaml:object, prose:str, declarations:object}` (E1.1.1) |
| `croissant` | object/null | the Croissant subset (E1.1.2), or null |
| `splits` | array | `{name:str, num_rows:int|null, num_bytes:int|null}` |
| `sample` | object | the `dsample/1` record (E1.2) |
| `license_files` | array (optional) | `{path:str, text:str}` for captured LICENSE/COPYING files — the W1 file-identification leg's only input (Phase-E2, D-37). **Present only when at least one LICENSE file was captured**; omitted otherwise, so snapshots without one (every Part A-D bench case) are byte-identical to Phase E1. |
| `snapshot_sha256` | str/null | canonical content hash (D-09 convention; the shared `content_hash` helper, schema-agnostic) |

### E1.1.1 `card.declarations` — the only claim surface (closed vocabulary)

Extracted **deterministically** from `card.yaml`. W1–W7 may use exactly these
fields; nothing else in a card is visible to them (design hard rule: no prose
parsing). A field extracted with the wrong type yields its empty value and never
raises (D-27): scalar fields → `null`, collection fields → `[]`/`{}`.

| field | type | source |
|---|---|---|
| `license` | str/null | card YAML `license` (first value if a list, lowercased) |
| `languages` | array of str | card YAML `language` (ISO 639-1 codes; scalar is wrapped) |
| `pii` | str/null | `annotations.pii ∈ {"none","present"}`, else null |
| `decontaminated_against` | array of str | `annotations.decontaminated_against` (suite ids) |
| `dedup_rate` | number/null | `annotations.dedup_rate ∈ [0,1]`; out-of-range/wrong-type → null |
| `sources` | array | `annotations.sources`: `{name:str, license:str}` items (invalid items dropped) |
| `file_inventory` | array | `annotations.file_inventory`: `{path:str, rows:int|null}` items |
| `language_shares` | object | `annotations.language_shares`: `{code:number}` (W7; added to the vocabulary per the prompt) |

`annotations` is a card-YAML object; unknown keys inside it are ignored.

### E1.1.2 Croissant subset

`{license:str|null, distribution:[{name, contentUrl, sha256}], recordSet:[{name}]}`
— only these keys are read; anything else is ignored.

## E1.2 Sampling rule `dsample/1` (pinned)

Applies per split to row-oriented data files (jsonl/csv/parquet; bench stand-ins
are jsonl). Rows are addressed by their 0-based index in file order. Implemented
**once** (`snapshot/dsample.py`) and shared by both adapters and the bench
generator.

- **Selection**: a seeded reservoir (Algorithm R) over the split's row indices.
  The per-split RNG is `random.Random(split_seed)` where
  `split_seed = int.from_bytes(sha256(f"{seed}:{name}".encode()).digest()[:8],"big")`
  — derived with sha256 (not Python's salted `hash`) so it is reproducible across
  processes (D-28). Base `seed = 20261111` unless the command passes another
  (recorded). Reservoir: fill the first `cap_rows` indices, then for row `i ≥
  cap_rows` draw `j = rng.randint(0, i)` and replace slot `j` iff `j < cap_rows`.
  The retained rows are emitted **sorted by ascending index**.
- **Splits** are processed in ascending split-name order.
- **Caps**: `cap_rows = 2000` per split; `cap_bytes = 20·1024·1024` content per
  snapshot (hf_dataset). `local_dataset` honours `--sample-cap-rows` /
  `--sample-cap-bytes`; the rule id stays `dsample/1`, the actual parameters are
  recorded. The byte cap is enforced after reservoir selection by walking the
  retained rows in (split-name, index) order and including a row iff
  `cumulative_text_bytes + len(text.utf8) ≤ cap_bytes`, otherwise skipping it and
  continuing (D-28).
- **`sample` record**: `{rule:"dsample/1", seed:int, cap_rows:int, cap_bytes:int,
  per_split:[{split, rows_total:int|null, rows_sampled:int, bytes_read:int}],
  rows:[...]}` where `rows` holds `{split:str, index:int, text:str}`. `text` is
  the row's designated text field — the first **string** field named one of
  `text|content|prompt|completion|instruction` (that order), else the row
  serialized as canonical JSON (D-09 bytes, decoded). Non-row files (images,
  binaries) are inventory-only.
- **Determinism**: same input + same seed → byte-identical sample (tested).

## E1.3 W classes (pinned semantics)

Severity order and finding conventions follow §3.1/§4. `check ∈ "W1".."W8"`;
evidence `expected`/`actual` are strings or null. W8 is always `heuristic:true`,
`info`, never gate-counted. **Masking (hard, D-31)**: any detected PII/secret
value appears in findings/packs/reports/tests **only masked** — first 2 + last 2
characters (`ab••••••yz`); a value of length ≤ 4 is fully bulleted. Full values
never enter a finding, pack, report, or test expectation.

- **W1 License consistency** — `declarations.license` vs the license identified
  from LICENSE file(s) vs `croissant.license`: any resolvable pair that disagrees →
  `license_inconsistent` (high). Declared license absent from the license-terms
  table → `license_unknown` (low). **LICENSE-file leg (Phase-E2, D-37, live):**
  identification uses the `license_file_phrases` + `license_file_order` data in
  **`dataset-hub-v1` (1.1.0)** — `license-terms-v1` stays byte-unchanged (D-29).
  Normalization (pinned): lowercase → drop any line containing `copyright` or
  `(c)` → collapse all whitespace runs to a single space → strip; phrases match as
  substrings of the result. Identification walks `license_file_order` (significant
  — e.g. `lgpl-3.0-only` before `gpl-3.0-only`) and the **first** id whose
  `required` phrases all appear and whose `forbidden` phrases none appear wins.
  Covered ids: `apache-2.0`, `mit`, `bsd-3-clause`, `cc-by-4.0`, `cc-by-nc-4.0`,
  `cc0-1.0`, `gpl-3.0-only`, `lgpl-3.0-only`, `mpl-2.0`. No LICENSE file present or
  no id identified → the leg is **silent** (never guessed). Input is the optional
  `license_files` snapshot field; LICENSE files are captured path-sorted and the
  first that identifies wins.
- **W2 Declared source-license rollup** — over `declarations.sources` only. If the
  declared aggregate license is not in a source license's `derivative_may_declare`
  per `license-terms-v1` → `source_license_incompatible` (high, one per violating
  source, `subject` = source name). A source license unknown to the table →
  `license_unknown` (low). No sources → silent.
- **W3 Inventory truth** — `declarations.file_inventory` vs `files`/`splits`:
  declared path absent from `files` → `declared_file_missing` (medium); a data
  file present (ext `.jsonl/.csv/.parquet/.txt/.json`) but not declared, **when an
  inventory is declared** → `undeclared_data_file` (medium); a declared file's
  `rows` ≠ the row fact (the `num_rows` of the split whose name equals the file's
  basename without data extension; exact for bench, split metadata for hf),
  divergence > 0 → `row_count_mismatch` (medium). The declared-total-size leg is
  **silent** (the closed vocabulary carries no declared size surface — D-30). W3
  requires a declaration to fire (it grades claims, not existence).
- **W4 PII falsification** — detectors over `sample.rows[].text`, ids pinned:
  `card_luhn` (13–19 digit run passing Luhn), `iban_mod97` (IBAN-shaped, mod-97 ==
  1), `email` (`[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`), `ipv4` (four
  0–255 octets), `secret_aws` (`AKIA[0-9A-Z]{16}`), `secret_github`
  (`ghp_[A-Za-z0-9]{36}`), `secret_openai` (`sk-[A-Za-z0-9]{20,}`). One finding per
  (detector, row); evidence `{file: split, field:"sample", expected, actual}`,
  `actual` = masked value + detector id. If `declarations.pii == "none"` the code
  is `pii_claim_falsified` (high); otherwise `pii_detected` (medium). The pack
  never certifies PII absence; no findings means "none detected in the sample",
  which the report states.
- **W5 Benchmark contamination (measured)** — word-level 13-gram overlap between
  sample rows and `contamination-v1` suites. Normalization (pinned): lowercase →
  collapse whitespace runs to one space → delete characters not in `[a-z0-9 ]` →
  split on space. A row is contaminated if it shares ≥1 13-gram with a suite item.
  Per-suite rate = contaminated sampled rows / total sampled rows. If the suite is
  in `declarations.decontaminated_against` and rate > 0 →
  `decontamination_claim_falsified` (high, one per suite); otherwise each suite
  with rate > 0 yields `contamination_measured` (info).
- **W6 Dedup measurement** — MinHash over the sample: shingles = word 5-grams of
  the normalized text (W5 normalization); 128 permutations; base hash `h =
  int(blake2b(shingle.utf8, digest_size=8)) mod P`, `P = 2^61−1`; permutation `i`
  uses `(a_i,b_i)` from `random.Random(20261111)` (`a_i = randrange(1,P)`, `b_i =
  randrange(0,P)`, i = 0..127, in order), `minhash_i = min((a_i·h + b_i) mod P)`.
  Estimated Jaccard of two rows = matching-position count / 128; near-dup pair ≥
  0.8; a row with no shingles has no partner. Measured rate = rows with ≥1
  near-dup partner / total sampled rows. If `declarations.dedup_rate` is a number
  and `|measured − declared| > 0.05` → `dedup_rate_mismatch` (medium); otherwise a
  `dedup_measured` (info) finding carries the measured rate (W6 always emits
  exactly one finding — D-33).
- **W7 Composition drift** — language ID over sample rows with `lid-v1` (E1.5);
  per-language share = rows classified to that language / total sampled rows; rows
  below the confidence floor are `und`. If `declarations.languages` is non-empty:
  with `language_shares` present, a declared language whose `|measured − declared|
  > 0.10` → `language_share_mismatch` (medium); with `language_shares` absent, a
  declared language with measured share == 0 → `declared_language_absent`
  (medium), and a language with measured share ≥ 0.20 that is not declared →
  `undeclared_language_dominant` (medium).
- **W8 Dataset-card completeness (signal only)** — declaration-field presence vs
  the `dataset-hub-v1` field list; `heuristic:true`, `info`, code
  `card_field_missing`. Excluded from the scorer and every gate (like V8).

**Gate/scorer counting rule (pinned, D-31)**: recall/FP count only findings with
`heuristic == false` **and** `severity != "info"`. Thus W8 (info+heuristic),
`contamination_measured` (info) and `dedup_measured` (info) never count.

## E1.4 `contamination-v1` starter pack

`{pack_id:"contamination-v1", version, suites:[...]}`. Two synthetic suites —
`benchsuite-alpha` (40 items) and `benchsuite-beta` (40 items) — are built from
seeded text templates by the checked-in builder
`rules.build_packs.build_contamination_pack()` as `{suite_id, items_sha256,
items:[str]}` (no `kind` key). The committed JSON is the source of truth;
regeneration must be byte-identical (tested).

**Phase-E2 — real suites as n-gram hashes (version `1.1.0`, D-38).** Real public
benchmark suites are added in a second form: `{suite_id, kind:"ngram-hashes",
source_repo, source_revision, source_config, source_split, text_fields,
item_count, ngram_count, ngram_hashes_sha256, ngram_hashes:[hex]}`. A suite
stores **only the sha256 hashes of its normalized word 13-grams** (W5
normalization, D-32) — never raw benchmark text. Hashes are computed by the
builder from a pinned source snapshot cached under `fixtures/contamination/`
(the committed pack is the source of truth; the synthetic part regenerates
byte-identically, and the real part regenerates identically from the cached
snapshots, which record the source revision and item counts). Suites added:
`gsm8k-test` (`openai/gsm8k`, config `main`, split `test`, field `question`) and
`squad-validation` (`rajpurkar/squad`, config `plain_text`, split `validation`,
field `context`), fetched once via `python -m releaseseal.rules.build_packs
fetch` (HF datasets-server rows endpoint; never touched by tests). A suite that
cannot be fetched is reported not-run, never fabricated. **W5 supports both
kinds**: for `ngram-hashes`, a row is contaminated iff any of its normalized
13-gram sha256 hashes is in the suite's set (`ngram_hash_set`, the single shared
helper); the rate / finding logic (`contamination_measured` info, or
`decontamination_claim_falsified` high when declared decontaminated) is otherwise
identical to the items kind.

## E1.5 `lid-v1` (pinned, dependency-free)

Closed language set `{en, ja, zh, es, fr, de}` (+ `und`). Classifier: character
n-gram (n = 3,4,5) **summed** log-likelihood over per-language profiles.
`{pack_id:"lid-v1", version:"1.0.0", floor_logprob:number, margin:1.0,
profiles:{code:{ngram:logprob}}}`. Profiles are built once by
`rules.build_packs.build_lid_pack()` from short seed paragraphs composed for this
purpose (checked in with the builder); logprobs are `round(log(count/total), 6)`
over char n-grams pooled across n=3,4,5; the committed file is the source of truth
and regeneration is byte-identical (tested). Scoring a text: lowercase, collapse
whitespace; `score(lang) = Σ_ngram profile[lang].get(ngram, floor_logprob)` over
all n=3,4,5 char n-grams; classify = argmax; `und` when `top − runner_up <
margin` (margin = 1.0). No external LID library or downloaded model (D-34).

## E1.6 Evidence pack `pack/2`

Dataset snapshots produce `pack/2`: header `pack_schema:"pack/2"`; the
`snapshot_ref` record gains `snapshot_kind` (`"model"`/`"dataset"`). Chain,
offline verification, and report are otherwise as §7. `verify-pack` verifies both
`pack/1` and `pack/2`. **Model snapshots keep the `pack/1` code path byte-for-byte
(D-35)** — only dataset snapshots take the `pack/2` path.

## E1.7 Part A-D bench (mirrors §6 conventions)

The generator builds small synthetic dataset releases as **`dsnapshot/1` objects
directly** (tiny data files' content inlined via the shared `dsample/1`), never
directories. Dev split: **120 cases, seed 20261111** — W1–W7 each 12 (= 84) + 36
clean, including near-miss cleans (truthfully-declared `pii:"present"` with
detector-negative content — D-36 — honest numeric dedup within tolerance,
unusual-but-valid licenses, contamination measured on undeclared suites).
Manifest `bench-manifest-d/1`: same fields as `bench-manifest/1` with
`composition` over `"W1".."W7"` + `"clean"`; case records `{id:"dcase-%04d", kind,
expected, snapshot}`, `expected` a subset of `{"W1".."W7"}` (class ids only, never
free text, never severities, never W8). Scorer: per-class recall + clean FP
exactly as §6.3 with the E1.3 counting rule. Regeneration byte-identical (tested).

## E1.8 CLI (E1)

- `releaseseal dsnapshot --local <dir> [--sample-cap-rows N] [--sample-cap-bytes N] -o snap.json`
- `releaseseal dsnapshot --hf-dataset <repo> [--revision r] -o snap.json`
  (`--hf-dataset-fixture <bundle.json>` serves a recorded bundle offline)
- `verify` / `pack` accept a `dsnapshot` (dispatch on `schema_version`)
- `releaseseal bench-d generate [--seed N] -o <dir>`
- `releaseseal bench-d score --manifest <dir>/manifest.json`

## E1.9 GATE E1

PASS iff, on the Part A-D dev split: **per-class recall ≥ 0.90 for every W1–W7**,
**clean FP rate ≤ 5%**, and the full test suite (existing + new) is green. W8 is
excluded entirely. Self-assessed in `reports/phase-e1.md` with the measured
numbers; fabrication of results is prohibited.

---

# Module B — AIBOM import/export

This section is the single reference for the AIBOM subpackage (`src/releaseseal/bom/`,
extension design §4). It fixes every concrete shape **before implementation**;
where it and the extension design disagree, this section's pinned values win and
the choice is recorded in DECISIONS.md (D-42..). Module B is independent of the
V/W verification core and of the Part B-D audit: it reads BOM *documents* and
evidence packs, never snapshots-under-verification, and dispatches on nothing in
the core. All Module B JSON is canonical-serialized (D-09): same input → **byte-
identical** output.

**Decidable subset only (hard rule, extension design §2/§7).** Module B checks
only facts a machine can settle from the bytes in front of it: a hash equals a
hash, a declared license string equals another, a bom-ref exists in the document,
a file in the paired artifact set is or is not accounted for by some component.
Anything semantic — whether a license is *really* compatible, whether a dataset
*really* is the one described — is out of scope. When a claim's evidence is not
provided, the claim is **unverifiable** (a first-class, counted outcome), never a
finding and never a silent pass.

## B.1 Import — BOM document → facts

`import_bom(document) -> bomfacts/1`. Two source formats are recognized; the
format is detected from the document shape (never guessed from a filename):

- **CycloneDX ML-BOM (JSON, spec 1.5 / 1.6 / 1.7)** — detected by
  `bomFormat == "CycloneDX"` (or a top-level `components`/`metadata` with a
  `specVersion` in `{1.5, 1.6, 1.7}`). Read `metadata.component` (if present) and
  every entry of `components[]`. Classify each component by `type`:
  - `type == "machine-learning-model"` → kind `"model"`.
  - `type == "data"` **and** `data.type == "dataset"` → kind `"dataset"`.
  - any other `type` → kind `"other"` — carried in `components[]` (so it round-
    trips) **and** counted in `ignored` by its raw type (extension design §4:
    "record other types as ignored-with-count").
  Extract per component: `name`, `version`, `bom-ref`, supplier/publisher strings
  (`supplier.name`, `publisher`), `licenses[]` (each `license.id` or
  `license.name`, else an `expression`), `hashes[]` (`{alg → content}`, alg kept
  verbatim e.g. `"SHA-256"`), `externalReferences[]` (`{type, url}`). Dependency
  edges come from the top-level `dependencies[]` section (`{ref, dependsOn:[...]}`)
  and are attached to the component whose `bom_ref == ref`.
- **SPDX 3.0 AI profile (JSON-LD)** — detected by a `@context` mentioning spdx
  **or** a `@graph`/`spdxId` presence. Read graph elements whose `type` (or
  `@type`) is `software_Package` (accepting the `software_Package` /
  `Package` spellings). Map `spdxId → bom_ref`, `name → name`,
  `versionInfo → version`, `hasConcludedLicense` else `hasDeclaredLicense →
  licenses[]`, `hasDownloadLocation → externalReferences` (`type:"distribution"`),
  and `verifiedUsing` Hash objects (`algorithm`,`hashValue`) → `hashes`.
  Relationships with `relationshipType == "dependsOn"` (subject `from`/`element`,
  object `to[]`) → `depends_on` edges. Kind is `"model"` for an element carrying
  an AI/model profile marker (`AIPackage`, `typeOfModel`, or `profileConformance`
  naming `ai`), `"dataset"` for a dataset profile marker (`DatasetPackage`,
  `datasetType`), else `"other"`. **Any element shape that cannot be mapped to a
  package is emitted as `unmapped` (counted), never guessed into a component.**

**Facts shape (`bomfacts/1`):**

```json
{
  "schema_version": "bomfacts/1",
  "source_format": "cyclonedx-1.6",
  "components": [
    {"bom_ref": "pkg:…", "kind": "model", "name": "…", "version": "…|null",
     "licenses": ["apache-2.0"], "hashes": {"SHA-256": "…"},
     "depends_on": ["other-bom-ref"]}
  ],
  "ignored": {"library": 2},
  "unmapped": 0
}
```

- `source_format ∈ {"cyclonedx-1.5","cyclonedx-1.6","cyclonedx-1.7","spdx-3.0-ai"}`.
- `components[]` holds model + dataset + other components, each with the fields
  above (all keys present; `version` nullable; `licenses`/`depends_on` arrays,
  `hashes` an object). Component order is **document order** (metadata.component
  first when present), preserved as read — not re-sorted — so import is a faithful
  transcription.
- `ignored`: `{raw_type: count}` for CycloneDX components whose type is neither
  model nor dataset (they are *also* in `components[]` as kind `"other"`; `ignored`
  is the transparency count the design asks for). Empty object when none.
- `unmapped`: count of document shapes (SPDX elements) that could not be mapped at
  all. `0` when none.
- **Determinism**: same document → byte-identical facts (no clocks, no set
  iteration order; dict keys serialized sorted by D-09).

## B.2 Verification — `verify_bom(facts, artifacts) -> bom-result/1`

The caller MAY pair the facts with an **artifact set** — the evidence the BOM's
claims are checked against. `artifacts` is `None` (not provided) or an object:

```json
{"files": [{"path": "model.safetensors", "sha256": "…|null"}],
 "license": "apache-2.0|null"}
```

An artifact set may be built from a model snapshot (`files[]` → `{path,sha256}`,
`card.claims.license` → `license`), a dataset snapshot (`files[]`,
`card.declarations.license`), or supplied directly as a directory listing with
hashes (the helper `artifacts_from_snapshot(snapshot)` does the snapshot cases).
`files[].sha256` may be null (hash unknown for that file).

**Decidable checks** (all findings use the `finding/1` shape with `check = "B1"`):

| code | severity | fires when |
|---|---|---|
| `bom_hash_mismatch` | high | a component hash and the paired artifact file matched by name carry the **same alg** but **different value** |
| `bom_license_mismatch` | medium | a component's declared license disagrees with the paired snapshot's declared license (`artifacts.license`), compared case-insensitively |
| `bom_dangling_ref` | medium | a `depends_on` edge names a `bom_ref` absent from the document's component set |
| `bom_undeclared_artifact` | medium | a weight/data file present in the artifact set that **no** component accounts for (by path or basename) |

- **`bom_dangling_ref` is a pure document check** — it needs no artifacts and
  always runs (one finding per dangling edge, `subject` = the missing ref).
- **Name matching** (hash & undeclared): a component matches an artifact file when
  the component `name` equals the file `path`, else when their basenames
  (last `/` segment) are equal. First match by document/listing order wins.
- **`bom_undeclared_artifact`** runs only when an artifact set is provided, and
  only for files whose extension marks them a weight or data file:
  `.safetensors .bin .gguf .onnx .pt .pth .h5 .msgpack .tflite .npz`
  (weights) or `.jsonl .csv .parquet .arrow .tfrecord` (data). Non-weight/non-data
  files (READMEs, configs, `.gitattributes`) never raise it.

**Unverifiable accounting (first-class, counted — extension design §4):** for
each component, its hash claim(s) and its license claim are *verifiable* only if
the matching evidence is present. Otherwise one `unverifiable` entry is emitted:

```json
{"component": "<bom_ref>", "claim": "hash|license", "reason": "<why>"}
```

- `claim == "hash"`: emitted once per component that declares ≥1 hash when no
  artifact set is provided (`reason: "no artifact set provided"`) or the component
  has no matching file in the set (`reason: "no matching artifact file"`). A
  component with no declared hashes contributes no hash claim.
- `claim == "license"`: emitted once per component that declares a license when no
  artifact set is provided or the set carries no declared license
  (`reason: "no declared license in artifact set"`).
- An unverifiable claim is **never** also a finding and **never** counted as a
  pass. A component whose hash *is* checked (match present) does not appear under
  `unverifiable` for `hash`.

**Result shape (`bom-result/1`):**

```json
{
  "schema_version": "bom-result/1",
  "source_format": "cyclonedx-1.6",
  "findings": [ { "check": "B1", "code": "bom_hash_mismatch", ... } ],
  "unverifiable": [ {"component": "…", "claim": "hash", "reason": "…"} ],
  "counts": {
    "findings": 1,
    "by_code": {"bom_hash_mismatch": 1},
    "unverifiable": 3,
    "unverifiable_by_claim": {"hash": 2, "license": 1},
    "components": {"model": 1, "dataset": 0, "other": 2},
    "ignored": 2,
    "unmapped": 0
  }
}
```

Findings are ordered by `(code, subject-or-component)`; `unverifiable` by
`(component, claim)` — both deterministic. Every `finding/1` carries real
`evidence` (`file`/`field`/`expected`/`actual`). Severities are as tabled; none is
`info`, so `B1` findings count like V1–V7 (not heuristic).

## B.3 Export — evidence pack → CycloneDX ML-BOM

`export_bom(pack, snapshot=None) -> <CycloneDX 1.6 JSON>`. The pack supplies the
release identity (`snapshot_ref.source`), the `snapshot_kind` (pack/1 → model;
pack/2 `snapshot_ref.snapshot_kind` → model/dataset), the snapshot digest
(`snapshot_sha256`), and the findings. The **optional** snapshot (D-42) supplies
the file inventory (with hashes where known) and the declared license — a pack
references its snapshot by hash and does **not** embed the inventory, so pack-only
export emits the release component + findings summary, and `--snapshot` adds the
file components and the release license.

Emitted document (`specVersion: "1.6"`, `bomFormat: "CycloneDX"`):

- `metadata.component` = the **release**. `bom-ref` = `"<repo_id>@<revision>"`
  (or `repo_id`, or `"release"` when neither is known). `type` =
  `"machine-learning-model"` (model) or `"data"` with `data.type = "dataset"`
  (dataset). `name` = `repo_id` (else `bom-ref`), `version` = `revision`.
  `licenses` = the declared license (from the snapshot) when known. The snapshot
  digest travels as `properties["releaseseal:snapshot_sha256"]` — **not** as a
  component hash (it is the digest of the snapshot JSON, not of any file; D-42).
- `components[]` = one per snapshot file whose `sha256` is known (`hash_source !=
  "none"` and non-null), `type: "file"`, `name` = file path, `hashes:[{alg:
  "SHA-256", content: sha256}]`. Files without a known hash are omitted (export is
  "with their sha256 hashes **where known**"). Emitted in path-sorted order.
- Findings summary travels in the metadata component's `properties`:
  `releaseseal:finding_count` = total, and one
  `releaseseal:findings:<check>` = count per check (e.g. `releaseseal:findings:V4`),
  values stringified. The non-certification discipline (SPEC §1/§10) carries over:
  properties state consistency findings only, never a compliance attestation.
- `properties["releaseseal:chain_tip"]` = the pack's `chain_tip`; `properties[
  "releaseseal:pack_schema"]` = the pack schema. No timestamps are invented beyond
  the pack's `created_at` (→ `metadata.timestamp` only if already a datetime; a
  bare date is carried as a property to keep output byte-deterministic).

**Round-trip rule (tested):** `import_bom(export_bom(pack, snapshot))` recovers the
same **component set** — the set of `(name, kind, hashes)` triples — as the export
wrote: the release (kind model/dataset) plus each emitted file component (kind
`"other"`, since `type:"file"` is not a model/dataset type — B.1). Licenses and
`depends_on` are not part of the round-trip invariant (export carries no
dependency edges; the release license round-trips when present).

## B.4 Mini-bench (`bench/bom_cases.py`, dev-only regression — no holdout)

`build_cases() -> bom-manifest/1` builds **24** deterministic cases. Marker
discipline mirrors §6/§E1.7: `expected` is a **subset of `{"B1"}`** for defect
cases and `[]` for clean — class ids only, never codes, never severities.

| group | n | expected | exercises |
|---|---|---|---|
| hash mismatch | 4 | `["B1"]` | `bom_hash_mismatch` (CycloneDX) |
| license mismatch | 4 | `["B1"]` | `bom_license_mismatch` |
| dangling ref | 4 | `["B1"]` | `bom_dangling_ref` |
| undeclared artifact | 4 | `["B1"]` | `bom_undeclared_artifact` |
| clean | 6 | `[]` | no finding; **one** case has a non-empty `unverifiable` list and still `[]` findings (artifacts withheld) |
| SPDX-import | 2 | one `["B1"]`, one `[]` | the SPDX importer end-to-end (one hash-mismatch defect, one clean) |

Manifest `bom-manifest/1`: `{schema_version, cases_sha256, composition, cases:[
{id:"bcase-%02d", kind, expected, format, bom:<document>, artifacts:<set|null>}]}`.
**Scorer (exact):** for each case, `import_bom(bom)` then `verify_bom(facts,
artifacts)`; the set of `B1`-producing cases must equal the set with non-empty
`expected`, and every clean case must yield zero `B1` findings. This bench is a
**regression suite, not a gate**; its result is reported in the phase report.
Regeneration is byte-identical (tested).

## B.5 CLI (Module B)

- `releaseseal bom import <bom.json> [--artifacts <snapshot.json>] -o result.json`
  — import then (with `--artifacts`, a model or dataset snapshot) verify; writes
  `bom-result/1`. Without `--artifacts`, every hash/license claim is reported
  `unverifiable` and findings are limited to `bom_dangling_ref`.
- `releaseseal bom export <pack.json> [--snapshot <snap.json>] -o bom.json`
  — emit a CycloneDX 1.6 document from an evidence pack (+ optional snapshot for
  file components and license).

## B.6 Scope / hard rules (Module B)

- Decidable subset only; everything semantic is `unverifiable`, never a finding
  and never a pass.
- `$0`, offline, deterministic (byte-identical output); tests never touch the
  network.
- Not a gate: the mini-bench is a regression check. No holdout (the class set is
  small and fully decidable).
