# DECISIONS

Interpretation decisions made while implementing Phase 1. The design doc
(`modelpass-design.md`) is authoritative; where it is silent or ambiguous, the
choice and its rationale are recorded here with a stable `D-NN` id. Changing a
recorded decision requires editing the entry, not the code silently.

---

### D-01 — Codename confinement

The design doc §0 requires the codename "ModelPass" be changeable in one
mechanical commit before any public artifact ships. Confinement strategy:

- The token `modelpass` appears structurally in exactly two places: the
  `[project].name` in `pyproject.toml` and the package directory `src/modelpass`.
- All intra-package imports are **relative** (`from ..snapshot import ...`), so
  no module hard-codes the package name.
- The human-facing codename string lives in one constant, `APP_CODENAME` in
  `src/modelpass/__init__.py`. Reports and evidence packs read it from there.
- Rename procedure (one commit): `git mv src/modelpass src/<newname>`, change
  `name` + `[project.scripts]` + `package-data`/`packages.find` target in
  `pyproject.toml`, and set `APP_CODENAME`/`APP_SLUG` in `__init__.py`.

### D-02 — Parameter estimate (V2)

The doc asks for a "derived parameter estimate" from `config.json` to check card
claims. We estimate decoder-only transformer parameter count analytically:

```
embeddings   = vocab_size * hidden_size
per layer    = attn(q,k,v,o) + mlp
  attn       = hidden*hidden                      (q proj)
             + 2 * hidden * (hidden * n_kv/n_head) (k,v proj, GQA-aware)
             + hidden*hidden                       (o proj)
  mlp(gated) = 3 * hidden * intermediate           (gate, up, down)
  mlp(plain) = 2 * hidden * intermediate           (up, down)
final        = lm_head (vocab*hidden) unless tie_word_embeddings
```

A claim is flagged only when it falls outside **±20%** of the estimate
(`V2_PARAM_TOLERANCE`). The estimate is a coarse cross-check, not ground truth;
the tolerance is wide on purpose so only gross mismatches (e.g. a "7B" card on a
1.5B config) fire. Recorded because the exact formula/tolerance is our choice.

### D-03 — Severity scale

Findings use an ordered severity: `info < low < medium < high`. CI/gate
thresholds compare against this order. V8 findings are always emitted at a fixed
`info` severity AND carry `heuristic: true`; they are excluded from every
severity rollup used for gates (design §4.2, §9).

### D-04 — Finding & evidence-pointer shape

Each finding is a flat JSON object (see SPEC.md §4). The evidence pointer is a
sub-object `{file, field, expected, actual}` where any field may be `null`.
`expected`/`actual` are stored as strings (or `null`) so packs diff cleanly and
are schema-stable across types. Chosen over free-form prose for diffability.

### D-05 — Evidence-pack hash chain

The pack is a list of ordered records (header, snapshot-ref, then one record per
finding). Each record carries `prev` = sha256 of the previous record's
canonical JSON (sorted keys, no whitespace), genesis `prev` = 64 zeros. The
pack's top-level `chain_tip` = sha256 of the last record. `verify-pack`
recomputes the chain and the snapshot hash offline. Tamper with any record and
every subsequent `prev` and the tip change.

### D-06 — Bench case schema (value types & markers)

Per the MemSeal v2 lesson quoted in the prompt, SPEC.md §6.2 fixes the case
manifest value types exactly. Markers (expected finding identifiers) are the
short check-class ids `"V1".."V7"` only — never free text. A clean case lists
`expected: []`. The generator is seeded; the manifest records `seed`,
`cases_sha256`, and the per-class composition.

### D-07 — License lineage source (V3)

`base_model` and `base_model_relation` come from the card YAML in the snapshot
(HF's standard card fields). Lineage is the transitive `base_model` chain; each
hop's license is whatever that ancestor release *declares* (in synthetic bench,
provided per node; for `hf`, the ancestor's own card license when snapshotted).
When an ancestor's license is not in `license-terms-v1`, V3 emits a
`license_unknown` finding (severity `low`) rather than guessing compatibility —
"判定不能" per the prompt, never an inferred compatible verdict.

### D-08 — V8 fingerprint

The config fingerprint is a tuple of architecture-defining fields
(`model_type, hidden_size, num_hidden_layers, num_attention_heads,
num_key_value_heads, vocab_size, intermediate_size`). `fingerprints-v1.json`
maps a fingerprint hash → known base id. V8 fires only when `base_model` is empty
AND the fingerprint matches a table entry. Always `heuristic:true`, `info`
severity, never gate-counted.

### D-09 — Snapshot hashing

The snapshot's identity hash (`snapshot_sha256`, used by evidence packs) is
sha256 over the canonical JSON of the snapshot **content** excluding the
`snapshot_sha256` field itself. Canonical = `json.dumps(sort_keys=True,
separators=(",",":"), ensure_ascii=False)` UTF-8 encoded. Used everywhere a
canonical hash is needed, so determinism is centralised in one helper.

### D-11 — HF fixtures authored to schema (not live-captured)

The design wants the `hf` adapter tested against *recorded* API responses from
2–3 small public repos. This build environment has no network ($0, offline
tests), so `fixtures/hf/*.json` are authored to the documented HF Hub API
response shape (model info `sha`/`cardData`, tree entries with `lfs.sha256`,
small file bodies) rather than captured live. They exercise the adapter's
parsing of the real shape. Capturing live bundles via `hf_live.HttpFetcher` is a
Phase-2 smoke task and requires no adapter code change. Disclosed in
`reports/phase1.md` as a known limitation.

### D-12 — hf adapter does not resolve ancestor licenses in Phase 1

The `hf` adapter fills lineage only from what the card declares; it does not
recursively fetch ancestor repos (would need a fixture per ancestor / network).
So V3 on an hf snapshot with a declared `base_model` but no resolved lineage
emits `license_unknown` ("undeterminable"), never a guessed compatible verdict —
consistent with the prompt's "判定不能" rule. Recursive lineage resolution is
Phase-2 work. The synthetic bench supplies `lineage` explicitly, so V3's
compatible/incompatible/attribution logic is fully exercised there.

### D-10 — `as of` staleness reference date (V5)

V5 flags past `as-of` dates. "Past" is judged against a caller-supplied
`as_of_now` date threaded into the verification context (default: the snapshot's
own `captured_at`), never `datetime.now()`, to keep verification deterministic
and reproducible from the snapshot alone.

---

## Phase 2

### D-13 — Rename codename "ModelPass" → public name "ReleaseSeal"

The owner chose the public name **ReleaseSeal** on 2026-11-08. Executed the D-01
mechanical rename: `git mv src/modelpass src/releaseseal`; `pyproject.toml`
`name`/`scripts`/`package-data`; the `APP_CODENAME`/`APP_SLUG` constants; the
`hf_live.py` User-Agent (`modelpass-smoke/0.1` → `releaseseal-smoke/0.1`, the
third literal the Phase-1 audit flagged); doc product names (README, SPEC,
bom-mapping). The codename history is **kept, not erased**, in DECISIONS.md
(D-01..D-12 stand as written) and STATUS.md. Verified post-rename: all tests
green and the dev bench regenerates byte-identically (`cases_sha256`
`5267e1a0…` unchanged), confirming the name never leaked into bench data.
Design-era filenames (`modelpass-design.md`) and the working-directory name are
left as historical artifacts; `reports/phase1.md` is a dated record and is not
rewritten.

### D-14 — Recursive lineage flattening (closes audit note 1)

The `hf` adapter now resolves the `base_model` chain recursively (depth cap 8,
cycle guard by visited repo-id set) via the fetcher: each ancestor's
`model_info` yields its declared license and its own `base_model`. The result is
a flattened `lineage` map (ancestor-id → `{license, requires_notice-source,
notice_present_in_ancestor, depth, parent}`) stored on the snapshot, so V3 walks
*all* ancestors, not just direct parents. Unreachable ancestors or licenses
absent from `license-terms-v1` are recorded as `license_unknown` (never guessed
compatible — D-07 rule holds at every depth). The `local` adapter continues to
accept an optional `lineage.json` sidecar, now documented as the multi-level
form. Supersedes the Phase-1 limitation in D-12 for the recursive case.

### D-15 — dev_ext is a separate, additive manifest

The frozen Phase-1 dev split (120 cases, `cases_sha256` `5267e1a0…`) is **not
modified**. Multi-level lineage cases (grandparent violation, unknown
intermediate, deep-attribution failure, deep clean) ship as `dev_ext` with its
own manifest and `cases_sha256`, generated by a separate seeded routine. The
scorer gains a `lineage-walk accuracy` metric (design §5): fraction of lineage
cases whose detected violating-ancestor set matches the planted one.

### D-16 — Part B / holdout provenance

Part B snapshots are fetched live from the HF Hub API (metadata + small files
only; no weight bytes; capture date + resolved revision recorded per model). The
target list is frozen in `bench/partb/models.json` before the run and never
swapped afterward. The holdout (`~/Desktop/Claude code/ModelPass-holdout/`) is
scored once with the frozen verifier if delivered; as of this session it is
**not delivered**, so GATE 2 is judgment-pending and the report completes through
Part B.

### D-17 — Heuristic weaknesses surfaced by Part B (recorded, NOT fixed in-run)

Part B (frozen code) surfaced false-positive patterns in the heuristics. They are
recorded here as spec/implementation discrepancies to fix in a future rule-pack /
code revision; they were **not** patched mid-Part-B (the audit must run the frozen
verifier, and tuning after seeing results is forbidden). None affects GATE 1 (the
synthetic bench co-designs claims with the checks) or the frozen dev `cases_sha256`.

1. **V2 param estimate overcounts tied embeddings** — when `config.json` omits
   `tie_word_embeddings`, the estimate adds a second vocab×hidden matrix (gpt2,
   opt: ~162M vs true ~124M). Fix: infer tying by model_type default, or widen
   tolerance for the embedding term.
2. **V2 param-claim extraction grabs non-param numbers** from prose — training
   *token* counts (t5-small "623b") and *sibling* model sizes (Yi-6B "34B"). Fix:
   require the number to be adjacent to "parameter(s)"/"params", or prefer a
   structured field.
3. **V2 context check ignores `rope_theta`** — Yi-6B extends context via large
   `rope_theta`, not a `rope_scaling` dict, so context_mismatch false-fires. Fix:
   also exempt a non-default `rope_theta`.
4. **V6 unsourced_claim too broad** — the `word: number` prose regex matches
   hyperparameters (`num_gpus: 8`, `batch_size: 8`) and training-curve values
   (loss, perplexity). Fix: restrict to benchmark-named lines or a known-metric list.
5. **V7 tokenizer detection misses `spm.model`** (deberta-v3) and other SPM
   variants. Fix: add `spm.model`/`sentencepiece.bpe.model` to the tokenizer-file set.

These are precision limitations on real cards; the robust large-scale signal in
Part B is V4 (documentation gaps). Addressing 1–5 is a Phase-3 prerequisite before
any public per-model assertions.

### D-18 — GATE 2 result: FAIL (independent holdout), and the weaknesses it surfaced

The sealed holdout (84 cases, `cases_sha256` 2dd678fd…, authored by a separate
session from the spec alone) was scored **once** with the frozen verifier (D-17
fixes held; no tuning). No manifest value-shape conversion was needed (formats
matched). Result: recall V1–V4 = 1.000, V5 = 0.750, V6 = 0.500, V7 = 0.875;
clean FP = 1.000. **GATE 2 = FAIL** (recall floor 0.85 missed on V5/V6; FP ceiling
5% missed at 100%). V3 multi-level recall = 1.000 across all subtypes — the
recursive lineage walk (D-14) generalised.

Root cause is overfitting that GATE 1 (co-designed synthetic) could not reveal:
- **V4 keyword brittleness → 100% clean FP.** The gpai-eu pack matches fixed
  substrings; independently-worded compliant cards register false Annex gaps
  (e.g. "testing process", "input and output" vs "inputs and outputs",
  "distribution channel"). Top blocker. Fix: synonym/structured detection.
- V6 prose detector parses only `Benchmark: number` lines, not natural sentences
  (recall 0.50). V5 ignores `result_files` source checkpoints (recall 0.75). V7
  misses chat-template-file references on non-chat-tagged models (recall 0.875).
- Tied-embedding param estimate (D-17 #1) confirmed: 2 clean V2 false positives.

Decision: results stand unmodified (the whole point of a sealed holdout). The
fixes (D-17 #1–5 + the four above) are a prerequisite for any gate re-attempt or
Phase-3 public audit; a re-attempt needs a *fresh* independent holdout, since
this one is now un-sealed by scoring. Holdout cases were not imported into the
repo; only aggregate scores (`audit/holdout/score.json`) are kept.

### D-19 — D-17/D-18 fixes applied (post-GATE-2)

Applied the heuristic fixes after GATE 2 FAIL, on the owner's instruction:
- **V2** param estimate accepts tied/untied range when the config omits
  `tie_word_embeddings` (D-17 #1); claim extractor requires a parameter context,
  so training-token counts and sibling-model sizes are no longer misread
  (D-17 #2); context check exempts a large `rope_theta` (D-17 #3).
- **V4** gpai-eu pack → **v1.1.0**: broadened synonym keywords + normalised,
  depluralised matching so natural phrasing satisfies Annex items (D-18 #6).
  (Dropped the over-lenient `model_index_present` satisfier on `xi.testing_process`
  — results existing does not describe the testing *process*.)
- **V5** reads `result_files` for recorded source checkpoint/revision drift (D-18 #8).
- **V6** detects natural-sentence eval claims and excludes a hyperparameter /
  training-curve stoplist (D-17 #4, D-18 #7).
- **V7** recognises `spm.model`/SentencePiece tokenizers (D-17 #5) and flags a
  `chat_template_file` reference to an absent file (D-18 #9).

Validation (no tuning against the un-sealed holdout): GATE 1 stays PASS (dev
recall all 1.000, clean FP 0.000; `dev_ext` lineage-walk 1.000; frozen dev
`cases_sha256` `5267e1a0…` unchanged); 9 regression tests added (61 total, all
offline-green); re-verifying the saved Part B snapshots with the fixed code drops
false positives V2 21→14, V4 376→296, V6 10→5, V7 1→0. A real GATE 2 re-attempt
requires a **fresh** independent holdout (the prior one is un-sealed by scoring);
the fixes were validated only against dev + unit tests, never the old holdout.

## Phase 2 — fix completion round

### Correction to D-18 / D-19 (appended; originals left intact)

D-18 and D-19 attributed the two clean V2 false positives (holdout v1 cases
0062/0067) to the **tied-embedding** estimate. **That attribution was wrong.**
Direct verification: both cases are `gpt_neox` configs, and the real cause is the
**gated-MLP (FFN) structure** — the estimator counted gated (3-matrix) families
as plain (2-matrix), under-counting by `hidden*intermediate` (46,137,344 for that
config). The tied/untied range (D-17 #1) is a *separate, real* fix for Part B's
tied-embedding models (gpt2/opt); it does not fix the gated-MLP cases. The
gated-MLP fix is D-21 below.

### D-20 — Rule-pack version discipline restored

The remediation round edited `gpai-eu-v1.json` in place to an internal 1.1.0,
breaking the versioning rule. Fixed: `gpai-eu-v1.json` is **restored to 1.0.0**
(from git `8feef98`) so the frozen Part B v1 run reproduces with pack 1.0.0; the
broadened/robust matching ships as a **new** `gpai-eu-v2.json` (2.0.0). The
verifier default pack set switches `gpai-eu-v1` → `gpai-eu-v2`
(`rules/__init__.py` `DEFAULT_PACK_IDS`). `test_rules.py` asserts both versions
exist. Loading `pack_ids=("...","gpai-eu-v1",...)` reproduces v1 behaviour.

### D-21 — FFN structure chosen deterministically by model_type

`estimate_params` selects the MLP structure from `config.model_type`: gated
(3-matrix SwiGLU) for `_GATED_FAMILIES`, plain (2-matrix) otherwise. The audit
found `gpt_neox` missing from the gated set, so it was under-counted; `gpt_neox`
(and the `gptneox` spelling) are **added**. The authoritative gated set is:
llama, mistral, mixtral, qwen2, qwen2_moe, qwen3, gemma, gemma2, phi3, stablelm,
starcoder2, gpt_neox, gptneox. Regression tests: a gated model stating its true
(gated) count is not flagged; a 4× claim still is. Residual risk (recorded for
the re-gate predictions): a genuinely plain-MLP model that re-uses a gated
family's `model_type` could now be over-counted — a V2-direction risk to watch.

### D-22 — Provider-document items: substantive phrase OR reference, not a word

v1's `cop.copyright_policy` was satisfied by the bare word "copyright" appearing
anywhere — semantically backwards from the spec (provider-level documents are
satisfied by a substantive card statement or a reference/location pointer). In
`gpai-eu-v2`, `cop.copyright_policy` and `cop.training_content_summary` are marked
`provider_doc` and satisfied by EITHER a specific multi-word phrase
(e.g. "copyright policy", "public summary of training content") OR a card
reference field (`yaml_fields`, e.g. `copyright_policy_url`). Bare generic words
("copyright", "summary", "data") are removed from their keyword lists, so word
presence alone no longer satisfies. dev / dev_ext remain complete (their clean
cards use the specific phrases). Regression tests cover bare-word (flagged),
phrase (satisfied), and reference-field (satisfied).

### D-23 — Revert gpt_neox to a plain MLP (match the real architecture)

**Reason.** D-21 placed `gpt_neox` in `_GATED_FAMILIES`. Real GPT-NeoX (Pythia,
GPT-NeoX-20B) uses a **plain** 2-matrix MLP (`dense_h_to_4h` / `dense_4h_to_h`,
GELU), not a gated 3-matrix SwiGLU. D-21's classification matched the v1 holdout
author's counting convention, not reality, and over-counts real NeoX models by
~`hidden*intermediate` (~24% on typical dims, beyond the ±20% tolerance). The
verifier must model the real architecture, not a test author's convention. Based
on public architecture facts, not sealed data.

**Change.** Removed `gpt_neox` / `gptneox` from `_GATED_FAMILIES`; estimate is now
plain for NeoX. Regression tests updated: a gated family (llama) stating its true
3-matrix count is clean; `gpt_neox` stating its true **plain** count is clean, and
a gated-inflated claim (+`hidden*inter`) is caught as `param_mismatch`.

**Impact.** On the disclosed holdout v1 regression, the two clean `gpt_neox`
cases (0062/0067) **return as V2 false positives (0 → 2)**. This is correct and
expected: those v1 clean cards state a *gated* (3-matrix) parameter count for a
`gpt_neox` config, which deviates from the real plain-MLP architecture — an
**author counting-convention deviation**, not a verifier regression. GATE 1 is
unaffected (the dev bench uses `llama` configs); dev / dev_ext numbers and the
frozen dev `cases_sha256` are unchanged.

**Decider.** Audit finding → owner approval. Supersedes the `gpt_neox` addition in
D-21 (the deterministic-FFN-by-model_type mechanism in D-21 otherwise stands).

## Phase 2 — final alignment round

### D-24 — Content-word V4 matching (gpai-eu-v3)

Fixed-phrase / substring matching (v2) was brittle: a naive trailing-s strip
turned "modalities" into "modalitie", a single article moved "a summary of the
training content" outside a fixed phrase, and "validated by running the model
over an untouched held-out test set" matched no testing keyword. `gpai-eu-v3`
(3.0.0) replaces keywords with **content-word patterns**: each item has several
patterns (sets of content words); a pattern is satisfied when all its words —
**Porter-stemmed**, function words ignored — co-occur, order-independent, within
one **sentence window** (`verify/textmatch.py`). Sentence windows (not whole
prose) prevent a dropped section from leaking through words reused elsewhere.
Default pack switched to v3; v1/v2 retained for reproducibility. Validation: dev
V4 recall 1.000 / clean FP 0.000 unchanged; the three audit phrasing examples now
match; holdout v1/v2 phrasing misses resolved (residual clean FP on v1/v2 is the
item-set gap below, not phrasing).

Per-item pattern rationale (sources: Annex wording; dev bench sentences; disclosed
holdout v1/v2 cards; Part B real cards — all permitted dev/regression data):
architecture — structural (config) + "model/transformer architecture", "decoder-only".
training_process — "training process/procedure/recipe", "pretrain", "fine tune",
  "supervised/instruction fine", "train + {adamw,cosine,decay,optimizer,objective,
  end,step}" (holdout "Trained end to end with cosine decay").
testing_process — "testing process", "evaluation procedure/methodology/protocol",
  "validate test", "held out {test,set}", "validation/test split" (holdout
  "held-out test set", "reserved validation split").
evaluation_results — structural (model-index) + "evaluation/benchmark result/score".
compute — "training compute", "compute budget/use/cost", "gpu hour",
  "accelerator day", "flop/petaflop/tpu day".
energy — "energy/power consumption", "carbon emission/footprint", "co2".
data_summary — "training {data,dataset,corpus}", "data {source,mixture,overview}",
  "{web,public,corpus} text", "web {page,book,crawl}", "{source,licensed} code",
  "filtered blend", "dataset composition", "source material" (holdout data sources).
intended_use — "intended use/task", "intend", "purpose", "suited", "appropriate",
  "use {case,generation}", "designed" (holdout "suited to…", "appropriate for…").
downstream_integration — "integration/integrate system", "downstream
  {provider,integration}", "technical integration", "deploy", "inference",
  "load model", "usage example".
acceptable_use — "acceptable use", "out scope", "prohibited use", "misuse",
  "responsible use", "restriction".
io_modality — "input output", "modality" (stem fixes modalities), "text
  {prompt,continuation,string,output,emit}", "token text", "accept text",
  "image audio".
license / parameters — structural (license field / param or config present).
distribution — "distribution channel", "distribute/download/available hub",
  "model {hub,repository}", "release page", "{download,obtain} model".
copyright_policy — provider_doc (phrase or `*_url` field): "copyright
  policy/right/licensing/data", "rights/licensing training data", "intellectual
  property"; bare "copyright" alone never satisfies (≥2 content words).
training_content_summary — provider_doc: "{summary training content} (any order)",
  "summary training data", "public summary training", "content disclosure/summary".

### D-25 — The 16-item set is single-sourced from the pack

The GATE-2 re-gate FAIL was half an item-set mismatch: the verifier gate-counted
`xi.compute`, `xi.energy`, `xii.downstream_integration`, `xii.acceptable_use`
(and others) that the holdout authoring briefs never listed. Fix: the active gpai
pack's 16 item IDs are the single source of truth; `docs/authoring-item-set.md` is
**generated** from the pack (`rules.render_authoring_item_set_md`), future briefs
are built from it, and `test_authoring_item_set_in_sync_with_pack` fails if the
file and the pack diverge (a pack item added/removed without regen breaks CI). The
16 IDs are fixed; v3 changes only the matching, not the set.

### D-26 — V6 compares prose values against structured records (scale-aware)

Previously a benchmark present in a structured record (model-index / result-file /
eval_claims) was treated as "sourced" and its prose value was never compared, so a
contradiction had no check form (the two re-gate V6 misses). Now, for a prose
claim whose benchmark is structured, the values are compared on a common 0-100
scale (a value ≤ 1 is read as a fraction and ×100); a disagreement beyond 2.0
fires `eval_value_mismatch`, a scale-only agreement is silent, and a benchmark
with no structured source remains `unsourced_claim`. Both-direction tests added.

---

## Extension program — Phase E1 (dataset-verification core)

Interpretation decisions for the dataset core (SPEC.md "Extension E1"; design
`releaseseal-extension-design.md` §3). Where the Phase-E1 prompt and the design
disagree, the prompt's pinned values win and the choice is recorded here (the
prompt's own rule). All E1 choices take the most conservative reading when a
pinned detail is under-determined (prompt §10: narrower claim surface, stricter
determinism), never silently widening scope.

### D-27 — dsnapshot declaration extraction: wrong-type → empty, never raise

`card.declarations` (§E1.1.1) is the only W1–W7 claim surface and is extracted
deterministically from card YAML. A field with the wrong type yields its empty
value and never throws: **scalar** fields (`license`, `pii`, `dedup_rate`) → `null`;
**collection** fields (`languages`, `decontaminated_against`, `sources`,
`file_inventory`, `language_shares`) → `[]`/`{}`. The prompt says "wrong type →
null"; for the collection-typed fields the empty collection is the type-correct
analogue of null (it leaves the dependent W-check silent, the conservative
outcome). `dedup_rate` must be a real number in `[0,1]` (bool rejected; out of
range → null). `pii` must be exactly `"none"`/`"present"`, else null. Invalid
`sources`/`file_inventory`/`language_shares` items are dropped individually.
`language_shares` ({code:number}) was added to the vocabulary per the W7 pin.

### D-28 — dsample/1 pinned algorithm

Per-split RNG seed is `int.from_bytes(sha256(f"{seed}:{name}").digest()[:8],"big")`,
**not** Python's `hash()` (which is salted by `PYTHONHASHSEED` and would break
cross-process reproducibility). Selection is reservoir Algorithm R
(`rng.randint(0,i)`; replace slot iff `< cap_rows`); retained rows are emitted
**sorted by ascending index**. Splits are processed in ascending name order. The
byte cap is enforced after reservoir selection by walking retained rows in
(split-name, index) order and **skipping** any row that would exceed `cap_bytes`
(continuing past it), so as many small rows as fit are packed deterministically.
`text` = first STRING field in `text|content|prompt|completion|instruction` order,
else the row's canonical JSON (D-09 bytes decoded). Byte-identical for equal
(input, seed) — tested.

### D-29 — W1 LICENSE-file identification leg is silent (license-terms-v1 unchanged)

The prompt pins LICENSE-file license identification "by the license-terms table's
file-fingerprint entries" **and** requires `license-terms-v1` be reused unchanged.
The shipped pack ships no file-fingerprint entries, and adding them would both
change the frozen model Part B `rule_packs` and break the `pack/1` byte-for-byte
guarantee (D-35). Conservative resolution: the LICENSE-file leg is inert (silent),
exactly as the prompt permits ("if no LICENSE file or unidentifiable, that leg is
silent"). W1 therefore operates on declared-vs-croissant disagreement
(`license_inconsistent`, high) and declared-not-in-table (`license_unknown`, low).
Recorded as a coverage limitation for a future rule-pack revision.

### D-30 — W3 declared-total-size leg is silent; row-fact association

The closed declaration vocabulary (§E1.1.1) carries no declared total-size field
(`file_inventory` items hold `{path, rows}` only; Croissant distribution has no
size), so the `size_mismatch` leg has no declared input and is silent by
construction. W3 fires via `declared_file_missing`, `undeclared_data_file`
(data extensions `.jsonl/.csv/.parquet/.txt/.json`, only when an inventory is
declared), and `row_count_mismatch`. The row fact for a declared file is the
`num_rows` of the split whose name equals the file's basename without its data
extension (`train.jsonl` → split `train`) — exact for bench, split metadata for hf.

### D-31 — dataset gate/scorer counting rule + PII masking

Recall/FP count only findings with `heuristic == false` **and** `severity !=
"info"` (`gate_counted_dataset`), per the prompt's §7 scorer rule. This excludes
W8 (info+heuristic) and the `contamination_measured` / `dedup_measured` info
measurements. **Masking (hard):** any detected PII/secret value appears in
findings, packs, reports and test expectations only masked — first 2 + last 2
characters (`ab••••yz`); a value of length ≤ 4 is fully bulleted. Tests assert the
full values never appear. `pii == "none"` → `pii_claim_falsified` (high);
otherwise `pii_detected` (medium).

### D-32 — W5 normalization + contamination-v1 builder

W5 normalization (pinned): lowercase → collapse whitespace to one space → **delete**
characters not in `[a-z0-9 ]` → split on whitespace; a row shares a 13-gram with a
suite item on word-level 13-grams. Per-suite rate = contaminated rows / total
sampled rows; `decontamination_claim_falsified` (high) if declared decontaminated
and rate > 0, else `contamination_measured` (info). `contamination-v1`
(benchsuite-alpha/beta, 40 items each) is built by the checked-in
`rules.build_packs.build_contamination_pack()` from index-deterministic templates;
the committed JSON is source of truth and regenerates byte-identically (tested).

### D-33 — W6 MinHash construction

Shingles = word 5-grams of the W5-normalized text. Base hash `h =
int(blake2b(shingle, digest_size=8)) mod P`, `P = 2^61−1` (stdlib, unsalted). 128
permutations `(a_i,b_i)` from `random.Random(20261111)` (`a=randrange(1,P)`,
`b=randrange(0,P)`, i=0..127 in order); `minhash_i = min((a_i·h+b_i) mod P)`.
Estimated Jaccard = matching positions / 128; near-dup ≥ 0.8; a row with < 5 words
has no shingles and no partner. Measured rate = rows with ≥1 partner / total. W6
always emits exactly one finding: `dedup_rate_mismatch` (medium) iff a numeric
`dedup_rate` is declared and `|measured − declared| > 0.05`, else `dedup_measured`
(info).

### D-34 — lid-v1 construction + W7 semantics

`lid-v1` is a dependency-free character 3/4/5-gram classifier over per-language
profiles built by `rules.build_packs.build_lid_pack()` from short seed paragraphs
(composed for this purpose; `en/es/fr/de/ja/zh`). `logprob = round(log(count/total),
6)` over n-grams pooled across n=3,4,5; `floor_logprob = round(log(1e-6),6)`;
`margin = 1.0`. Scoring **sums** logprobs over the text's n-grams (so confidence
scales with length and the margin separates cleanly); classify = argmax, `und` when
top − runner-up < margin. The committed profile file is source of truth and
regenerates byte-identically (tested). W7 per-language share = rows classified to a
language / total; with `language_shares`, `|measured − declared| > 0.10` →
`language_share_mismatch`; without, measured 0 for a declared language →
`declared_language_absent`, and an undeclared language ≥ 0.20 →
`undeclared_language_dominant`.

### D-35 — pack/2 for datasets; model packs stay pack/1 byte-for-byte

Dataset snapshots (`dsnapshot/1`) produce `pack/2` (header `pack_schema:"pack/2"`;
`snapshot_ref` gains `snapshot_kind:"dataset"`). Model snapshots (`snapshot/1`)
keep the `pack/1` code path **byte-for-byte** — no `snapshot_kind`, `pack_schema
"pack/1"` — so the frozen model packs reproduce exactly (asserted in
`test_evidence_d.py`). `verify_pack` accepts both schemas; the `content_hash`
helper is schema-agnostic (excludes only `snapshot_sha256`), satisfying D-09 for
both snapshot kinds.

### D-36 — Part A-D near-miss clean `pii:"present"` uses detector-negative content

A clean case must raise no counted finding, and `pii_detected` (medium) counts.
So the "correctly declared PII-bearing" near-miss clean cases declare
`pii:"present"` but use detector-negative text (no sample hit → W4 silent,
`expected == []`). The honest-disclosure semantics the prompt names (declared
present + a detector hit → `pii_detected` medium, never falsification, never high)
are exercised directly in a unit test rather than as a bench clean, keeping the
clean FP at 0 without weakening the claim. Part A-D: 120 cases, seed 20261111,
`cases_sha256` `0e2633a2…`; GATE E1 recall all 1.000, clean FP 0.000.

### D-37 — W1 LICENSE-file leg goes live via dataset-hub-v1 1.1.0 (E1's D-29 superseded in effect)

Phase-E2 Step 1 switches on W1's third leg. D-29 parked it as silent because the
only pinned place for identification data was `license-terms-v1`, which must stay
byte-unchanged (it feeds the frozen model Part B `rule_packs` and the `pack/1`
byte-for-byte guarantee, D-35). Resolution: the identification data lives in
**`dataset-hub-v1`** instead, bumped `1.0.0 → 1.1.0`, as `license_file_phrases`
(per id: `required` — ALL must appear — and `forbidden` — NONE may appear) plus
`license_file_order` (evaluation order; significant, e.g. `lgpl-3.0-only` before
`gpl-3.0-only`). `license-terms-v1` is untouched, so D-29's hard constraint
stands and the model side is unaffected. Normalization is pinned in SPEC and in
the pack (`license_file_normalization`): lowercase → drop any line containing
`copyright`/`(c)` → collapse whitespace → strip; phrases match as substrings.
LICENSE text reaches the check through a new **optional** `dsnapshot/1` field
`license_files` (`{path, text}`), captured by both adapters for
`LICENSE*`/`COPYING*` files, path-sorted; the first id that identifies wins. The
key is present only when a LICENSE file was captured, so every Part A-D bench
snapshot is byte-identical to E1 (`cases_sha256` `0e2633a2…` unchanged, recall
1.000, clean FP 0.000 re-verified). No LICENSE file or no identified id → the leg
is silent (never guessed), exactly as the prompt permits.

### D-38 — contamination-v1 1.1.0: real benchmark suites as 13-gram hashes

Phase-E2 Step 2 adds real public benchmark suites to `contamination-v1`
(`1.0.0 → 1.1.0`). Hard constraint from the design (§7 no absence certification,
and avoiding redistribution of benchmark text): a real suite stores **only the
sha256 hashes of its normalized word 13-grams** (W5 normalization, D-32) under
`kind:"ngram-hashes"`, never the raw benchmark text. The two synthetic suites
are untouched (still plain `items`, no `kind` key), so their byte-identical
regeneration test is unchanged. W5 gains a hashed-suite leg: a row is
contaminated iff any of its 13-gram sha256 hashes is in the suite set; the shared
`ngram_hash_set` helper is the single source of the hashing so the builder and
the check can never drift. Suites: `gsm8k-test` (`openai/gsm8k`/main/test,
`question`; rev `740312ad…`, 1319 items → 45,164 hashes) and `squad-validation`
(`rajpurkar/squad`/plain_text/validation, `context`; rev `7b6d24c4…`, 523 unique
contexts from the first 3000 rows → 46,276 hashes). SQuAD *questions* are mostly
shorter than 13 words (no 13-gram), so the `context` field is used and contexts
are deduped — recorded in the fixture. The sources are fetched once
(`build_packs fetch`, HF datasets-server) into `fixtures/contamination/*.json`
(the pinned source snapshots, checked in); `build_contamination_pack()` and the
tests only read them, so regeneration is byte-identical offline. A suite that
cannot be fetched is skipped and reported not-run, never fabricated. Re-verified:
dataset bench clean FP stays 0 (no spurious real-suite overlap on the synthetic
clean cases), recall 1.000, `cases_sha256` `0e2633a2…` unchanged.

### D-39 — Croissant license normalized to an SPDX id (W1 real-data integrity)

HF auto-generates Croissant metadata for most datasets, and its `license` field
is frequently a URL (`https://choosealicense.com/licenses/apache-2.0/`) or an
SPDX URL rather than the plain id the card declares. Fed raw into W1's
declared-vs-croissant leg, that would manufacture `license_inconsistent` (high)
on virtually every Croissant dataset — a format artifact, not a real
inconsistency, and a dishonest Part B-D headline. `croissant_subset` now
normalizes the license to an SPDX-ish id: last path segment of a URL, drop a
`.html/.txt/.md/.json` suffix, lowercase/strip. A plain id (bench data, author
Croissant) is unchanged apart from case, so the Part A-D bench and its
`cases_sha256` are unaffected. A genuine declared-vs-Croissant license
disagreement still fires; only format noise is removed.

### D-40 — Part B-D audit operational pins (selection, sampling cap, on-disk redaction)

Part B-D audits other people's public datasets live. Three operational choices,
all recorded so the run is reproducible and honest:

1. **Selection** (`select_partbd.py`, frozen to `bench/partbd/datasets.json`,
   `partbd-datasets/1`): HF datasets sorted by downloads desc; keep public &
   not gated (`gated == False`) & not disabled & with ≥1 inventoriable data file
   (tree ext in `.jsonl/.csv/.parquet/.txt/.json`); greedily fill the strata
   (≥6 non-English/multilingual, ≥4 Croissant, ≥4 >1M rows, license families
   spread). Revisions pinned to the HEAD sha at freeze. Gated datasets are
   excluded, never authenticated against. Frozen & committed before the audit.
2. **Sampling cap**: the live `DatasetHttpFetcher` fetches the datasets-server
   rows endpoint for the first `max_splits = 2` splits, `rows_per_split = 200`
   (a prefix window, §3.2's "first-K rows where row access is structured"). The
   rule id stays `dsample/1`; the actual parameters are recorded in
   `summary.json.sample_params`, and each snapshot keeps the TRUE split totals
   (datasets-server `/size`) so coverage (sampled / total) is honest. A dataset
   whose rows cannot be fetched (script/unsupported) records an empty sample;
   one dataset never aborts the run.
3. **On-disk redaction**: the evidence pack's W4 findings are masked (D-31). The
   on-disk snapshot file additionally OMITS the raw sample row text
   (`sample.rows = []`, `rows_omitted_for_privacy`, `content_redacted_for_privacy`)
   — raw third-party content / possible PII is never persisted to the repo. The
   pack's `snapshot_ref.snapshot_sha256` is the hash of the full verified
   snapshot; the redacted file records it as metadata, not as a re-validatable
   body.

### D-41 — Part B-D fetcher picks the largest ROW-SERVED config (coverage, not tuning)

`DatasetHttpFetcher`'s config choice was corrected twice **before any audit
result was committed**, on principled coverage grounds, never toward the frozen
predictions:
1. v1 chose `configs[0]` — for `wikimedia/wikipedia` a tiny per-language config,
   so content-rich datasets showed `cov=0` (a tooling artifact).
2. v2 chose the config with the most rows — but the largest config is sometimes
   not row-served by datasets-server (e.g. `m-a-p/FineFineWeb`), which shadowed a
   smaller served text config and *lost* coverage.
3. **Final: the largest config whose rows endpoint actually serves rows** (try
   configs by total-rows desc, first that returns rows wins; `splits` reflects
   the config used, keeping the true totals as the coverage denominator). This
   recovers real content for wikipedia / FineFineWeb / fineweb-edu / MINT-1T.
The predictions (`reports/phase-e2-predictions.md`) stay frozen and untouched;
the final audit is reported as-is, hit or miss. Datasets datasets-server
genuinely does not row-serve at all (single-file `ShareGPT_Vicuna_unfiltered`,
some binary/parquet-only corpora) still record an empty sample + coverage note;
sampling their content would need a bulk download (out of scope, $0). A burst of
row requests triggered datasets-server rate-limiting mid-run (datasets that
provably serve rows showing `cov=0`), which corrupted coverage; the fetcher now
spaces calls (`min_interval`) and retries 429/5xx with backoff, so the recorded
run's coverage reflects what datasets-server actually serves, not throttling.
Coverage is still reported per dataset exactly as measured.

---

### D-42 — Module B export takes an optional snapshot; snapshot digest is a property, not a file hash

**Context.** SPEC Module B / extension design §4 describe `bom export` as taking an
evidence pack (`releaseseal bom export <pack.json>`), yet also require the exported
CycloneDX document to carry "files as components with their sha256 hashes where
known" and the "declared license". An evidence pack (`pack/1`/`pack/2`) references
its snapshot by hash (`snapshot_ref.snapshot_sha256`) but does **not** embed the
file inventory or the declared license — those live in the snapshot.

**Decision.** `export_bom(pack, snapshot=None)` and the CLI `bom export <pack.json>
[--snapshot <snap.json>]`. Pack-only export emits the release as the metadata
component plus the findings summary (valid, and round-trips to the release
component). `--snapshot` adds one `type:"file"` component per snapshot file with a
known sha256 (path-sorted) and the release's declared license. The snapshot digest
travels as `properties["releaseseal:snapshot_sha256"]`, **never** as a component
`SHA-256` hash: it is the canonical digest of the snapshot JSON (D-09), not of any
file, and asserting it as a file hash would be a false claim a consumer could try
to verify against bytes. The optional flag is a superset of the named CLI (the
pack-only form still works), so no existing contract is broken.

### D-43 — "other"-kind components are carried AND counted; SPDX non-packages are `unmapped`

**Context.** The import spec says CycloneDX components that are neither
machine-learning-model nor data/dataset are "recorded as ignored-with-count", while
the `bomfacts/1` shape lists `kind: "model"|"dataset"|"other"` — i.e. "other" is a
first-class component kind.

**Decision.** Reconciled with no contradiction: every CycloneDX component is
transcribed into `components[]` with kind model/dataset/other (so it round-trips
and stays visible), and non-model/dataset components are **additionally** counted
in `facts.ignored` keyed by raw type (e.g. `{"file":2,"library":1}`). This is the
transparency count the design asks for without dropping data. For SPDX, an element
that maps to no package at all is a distinct outcome: counted in `facts.unmapped`
(an integer), never guessed into a component. `verify_bom` surfaces both in
`counts.ignored` / `counts.unmapped`.

### D-44 — SPDX hash algorithm labels normalized to the CycloneDX spelling on import

**Context.** CycloneDX writes `{"alg":"SHA-256", ...}`; SPDX 3.0 writes
`{"algorithm":"sha256", ...}`. `verify_bom` compares a component's hash against a
snapshot's `sha256` and against other components' hashes by algorithm key.

**Decision.** On SPDX import, the algorithm label is normalized to the CycloneDX
spelling (`sha256`→`SHA-256`, `sha512`→`SHA-512`, etc.); the hash **content** is
never altered. So a hash imported from an SPDX document compares correctly against
a CycloneDX hash and against a snapshot's streamed/LFS `sha256`. Unknown algorithm
names are kept verbatim. This is a label canonicalization, not a semantic judgement
(the decidable-subset rule is untouched).

### D-45 — GATE E2 verdict computed by applying the fixed E2 bars to the scorer's raw output

**Context.** The GATE E2 bars are per-class recall ≥ **0.85** for every W1–W7 and
clean FP ≤ **5%** (SPEC §9b/§E1.9 discipline; Phase-E2 scoring prompt). The frozen
scorer (`src/releaseseal/bench/score_d.py`) exposes exactly one gate helper,
`gate_e1(...)`, whose default `recall_floor` is **0.90** (the E1 floor), and the
`bench-d score` CLI prints a line labelled "GATE E1 (recall ≥ 0.9, …)".

**Decision.** The GATE E2 verdict was computed by applying the fixed 0.85 / 0.05
bars **by hand** to the scorer's raw `recall` / `clean_fp_rate` output, rather than
adding an E2 gate function or passing `recall_floor=0.85` through a changed code
path. Changing or extending the verifier/scorer before or during the single
holdout scoring is forbidden (Phase-E2 hard rule: a re-score after any code change
voids the measurement), so the scorer was run exactly as frozen and the bar was
applied in the report. The measured recall (1.000 on every class) clears both the
0.85 and the 0.90 floors and the measured clean FP (0.000) clears the 0.05 ceiling,
so the hand-applied E2 verdict and the CLI's E1-labelled line agree. Recorded for
provenance: the verdict is PASS against the **E2** bars, not merely against the
scorer's built-in E1 line.
