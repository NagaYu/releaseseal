# STATUS — Extension Phase E3 PREP COMPLETE — publication pending owner confirmation

## Phase E3 — v2 publication update (prep only; nothing pushed/posted)

Built the **v2 public export** in place at `../ReleaseSeal-public` (v1 HEAD
`4d9dea6`): synced the current dataset + BOM code, tests, fixtures, packs,
`bench/partbd/`, SPEC/DECISIONS, and the E1/E2 reports; added the Module D + Module
B README sections; added the HF payload (`dev-d-manifest.json` `cases_sha256
0e2633a2…`, `partbd-summary.json`) and audit payload (`hf-audit/partbd-results.md`
+ 3 masked sample packs under `packs-d/`); added a static Part B-D panel to the
Space `index.html`. Report: `reports/phase-e3.md`. Drafts:
`reports/phase-e3-release-notes.md` (both repos), `reports/phase-e3-entrance-drafts.md`
(dev only).

- **GATE E2 = PASS** (audited): sealed holdout 120 cases, seed 20261112, recall
  W1–W7 all 1.000, clean FP 0.000. Carried with its caveat (synthetic + co-designed
  with the scoring vocabulary → not a real-world recall estimate); Part B-D (W8
  100%, claim violations ≈ 0, 2 HIT/4 MISS) is the honest real-data statement.
- **Hygiene scan PASS**: no `holdout_d` path, no `hcase-`, no full holdout
  `cases_sha256` in the export (the one full occurrence in the synced
  `reports/phase-e2.md` was truncated to the v1-precedent commitment form
  `fe09ca18…`); no `claude-code-prompt`/design docs; no email in public text
  (portfolio-only contact); shipped Part B-D packs re-scanned → 0 unmasked
  email/IPv4/secret hits. `example.org` synthetic planted-PII in the bench data is
  intended published test content, not personal data.
- **Export tests: 183 passed** offline; **CLI smoke** (`dsnapshot`+`verify` on a
  dataset fixture, `bom import` on a CycloneDX 1.6 fixture) ran offline.
- **Space step: DONE** (static panel added — the page's model Part B numbers are
  already a static embedded block, so a static dataset panel was cheap; no runtime
  fetching, no new tooling).
- v1 disclosures (model GATE 2 FAIL ×3; V4 screening-signal limitation) kept
  verbatim. LICENSE byte-unchanged (All Rights Reserved).
- **Nothing pushed, uploaded, posted, or released.** Publication (GitHub push + v2
  release, HF dataset upload, Space upload, entrance choice) is **pending the
  owner's separate final confirmation**, item by item — the checklist is in
  `reports/phase-e3.md`.

---

# STATUS — Extension Phase E2 COMPLETE — GATE E2 PASS (local only)

## Phase E2 — GATE E2 scoring (final session) — **PASS** (local only)

Scored the sealed holdout **exactly once** with the frozen verifier; no verifier
change before/during/after. Report: `reports/phase-e2.md`. Decision: **D-45**.

- Tree scored **`90292a4`**; holdout `bench/holdout_d/manifest.json` — 120 cases
  (W1–W7 × 12 + 36 clean, seed 20261112), `cases_sha256 fe09ca18…` re-verified
  against the D-09 canonical hasher. Predictions commit `f3b9cba` predates build
  code (`f077f8e`, `90292a4`).
- **Result:** per-class recall **W1–W7 all 1.000 (12/12 each)**, clean FP
  **0.000 (0/36)**; empty miss/FP detail list. GATE E2 bars (recall ≥ 0.85 all,
  clean FP ≤ 5%) → **PASS**. Verdict computed by applying the E2 bars to the
  scorer's raw output (the scorer's built-in gate helper carries the E1 0.90 floor
  — D-45); both agree.
- **Holdout predictions beaten/met** (predicted 0.85–0.97 recall, 0.02 FP →
  measured 1.000 / 0.000); conservative, the opposite of the Part B-D optimism.
  **Caveat:** holdout is synthetic + co-designed with the scoring vocabulary — a
  perfect synthetic recall is **not** real-world recall; Part B-D (2 HIT/4 MISS,
  ~0 claim violations) is the honest real-data statement.
- **GATE E1 regression re-run (repeatable):** dev `cases_sha256 0e2633a2…`
  unchanged, recall W1–W7 all 1.000, clean FP 0.000 → GATE E1 still PASS; full
  suite **183 passed** offline; model GATE 1 still PASS.
- **No re-score, no fabrication, local commit only.** Phase E3 is separate.

## Phase E2 — Module B (AIBOM import/export) — COMPLETE (local only)

Independent of the Part B-D session, the holdout, and GATE E2 (touches none).
Choices recorded as DECISIONS **D-42..D-44**. SPEC: new **Module B** section
(B.1–B.6), fixed before implementation. Report: `reports/phase-e2-bom.md`.

- New subpackage `src/releaseseal/bom/`: `facts.py` (import → `bomfacts/1`;
  CycloneDX 1.5/1.6/1.7 + SPDX 3.0 AI), `verify_bom.py` (→ `bom-result/1`: B1
  findings + first-class `unverifiable`), `export.py` (pack + optional snapshot →
  CycloneDX 1.6). CLI `bom import` / `bom export`.
- **Decidable checks** (`check="B1"`): `bom_hash_mismatch` (high),
  `bom_license_mismatch` (medium), `bom_dangling_ref` (medium, pure document),
  `bom_undeclared_artifact` (medium). Each tested +/-. Anything semantic →
  `unverifiable` (counted), never a finding and never a pass.
- **Mini-bench** `bench/bom_cases.py`: 24 cases (`bom-manifest/1`,
  `cases_sha256 312e000e…`), exact-match **24/24 PASS**. Regression suite, **not a
  gate**; no holdout.
- Round-trip (export→import recovers the component set), determinism (byte-identical
  output), and both importers all tested. Existing model + dataset suites green
  **unmodified** → **full suite 183 green** (141 prior + 42 new), offline, $0.
- `license-terms-v1` and the model `pack/1` path untouched; no snapshot/W-check
  code changed. **No push, no HF, no posts — local commit only.**

## Phase E2 build — predictions + W1 file leg + real contamination + Part B-D audit

Build half of Phase E2 (the holdout-authoring, holdout-scoring, and Module B
AIBOM halves are **other sessions**). Choices recorded as DECISIONS **D-37..D-41**.
Report: `reports/phase-e2-build.md`. Predictions: `reports/phase-e2-predictions.md`.
**No publication, no remote writes — local commits only.**

- **Step 0** — predictions preregistered + committed **first** (`f3b9cba`),
  unchanged since (hard rule 1).
- **Step 1** — W1 **LICENSE-file leg live**: `dataset-hub-v1` 1.0.0→1.1.0 adds
  `license_file_phrases` + `license_file_order` (9 ids, pinned normalization &
  order); `license-terms-v1` **byte-unchanged** (D-29/D-37). New optional
  `dsnapshot/1` field `license_files`; adapters capture LICENSE text; absent on
  every bench case → `cases_sha256` unchanged.
- **Step 2** — `contamination-v1` 1.0.0→1.1.0: real suites `gsm8k-test` (45,164
  hashes) + `squad-validation` (46,276) as `kind:"ngram-hashes"` — **13-gram
  sha256 only, never raw text** (D-38). Synthetic suites untouched; byte-identical
  regen from `fixtures/contamination/` offline.
- **Step 3** — Part B-D: **36** datasets frozen (`bench/partbd/datasets.json`,
  committed before the audit), audited live via `DatasetHttpFetcher` (metadata +
  `dsample/1`-capped sample; $0; 36/36 ok, 0 errors). Outputs in `audit/partbd/`
  (snapshots redacted of raw sample text; packs masked; `summary.json`
  `partbd-summary/1`).

### Part B-D predictions scored — 2 HIT / 4 MISS

- **HIT** P3 W4 detector hits 0.194 (≥0.15); **HIT** P6 W8 completeness 1.000 (≥0.50).
- **MISS** P1 any-counted 0.361 (≥0.60); P2 W1 inconsistency 0.000 (≥0.25);
  P4 W5 overlap 0.028 (≥0.10); P5 W7 language 0.028 (≥0.10).
- Honest reading: dataset cards carry almost none of the structured declarations
  the W-checks grade (W8 100%; claim violations ≈ 0 except one wikipedia W7
  single-config sampling artifact) → Module D's real-data value is **measurement
  at stated coverage**, not claim falsification. Content coverage is thin
  (19/36 text-sampled; 17/36 binary/not row-served). Predictions optimistic in the
  same direction the model GATE 2 history warned about.

### GATE E2 — **PASS** (scored in the final session; see the top of this file + `reports/phase-e2.md`)

- Regression re-run: Part A-D dev `cases_sha256` `0e2633a2…` unchanged, recall
  W1–W7 all **1.000**, clean FP **0.000** → GATE E1 still PASS. Model GATE 1 still
  PASS; generated packs byte-identical; `license-terms-v1` byte-unchanged; model
  `pack/1` untouched. **Full suite 183 green** (was 141 before Module B's 42),
  offline.

**$0 spend, local commit only — no push, no HF, no posts.** Holdout authoring,
holdout scoring (GATE E2 verdict), and Module B AIBOM are deliberately left to
their own sessions.

---

# (history) Phase E1 COMPLETE (dataset core; GATE E1 PASS; local only)

## Phase E1 — dataset-verification core (complete; nothing pushed/posted)

Built Module D's core per `releaseseal-extension-design.md` §3 and the Phase-E1
prompt. SPEC fixed first (`SPEC.md` "Extension E1"); choices recorded as
DECISIONS **D-27..D-36**. Report: `reports/phase-e1.md`.

- **Schema** `dsnapshot/1` + closed-vocabulary declarations (`snapshot/dschema.py`);
  **sampling** `dsample/1` shared by adapters + bench (`snapshot/dsample.py`);
  **adapters** `local_dataset` + `hf_dataset` (offline fixtures
  `fixtures/hf/dataset-*.json`).
- **Checks W1–W7 + W8 signal** (`verify/wchecks.py`, `verify/lid.py`); PII values
  masked everywhere (D-31). Core `verify()` dispatches on `schema_version`.
- **Packs**: `dataset-hub-v1` (W8) hand-authored; `contamination-v1` + `lid-v1`
  generated by the checked-in `rules/build_packs.py`, byte-identical on regen.
  `license-terms-v1` reused unchanged.
- **Evidence** `pack/2` for datasets (snapshot_kind); model `pack/1`
  **byte-for-byte unchanged** (D-35). `verify-pack` verifies both.
- **Bench Part A-D**: `bench/generate_d.py` + `bench/score_d.py`
  (`bench-manifest-d/1`); CLI `dsnapshot` + `bench-d generate|score`.

### GATE E1 — **PASS**

- Dev split 120 cases, seed **20261111**, `cases_sha256` `0e2633a2…`.
- Per-class recall **W1–W7 all 1.000** (12/12 each); **clean FP 0.000 (0/36)**;
  full suite **129 tests green** (72 existing unmodified + 57 new), offline.
- Co-designed-synthetic caveat stands (as GATE 1): independent sealed holdout +
  Part B-D are **Phase E2**, not authored here.
- Model side intact: frozen dev `cases_sha256` `5267e1a0…` unchanged; model
  GATE 1 still PASS; model `pack/1` byte-for-byte.

### Deviations (conservative reading, prompt §10)

- D-29 W1 LICENSE-file leg inert (license-terms-v1 kept unchanged) — W1 uses
  declared-vs-croissant + declared-in-table.
- D-30 W3 size leg inert (no declared size surface in the closed vocabulary).
- D-31 scorer counts non-heuristic, non-info only (W8 / measurement info excluded).
- D-36 near-miss clean `pii:"present"` uses detector-negative content; honest
  disclosure semantics proven in a unit test.

**$0 spend, offline, local commit only — no push, no HF, no posts.** Phase E2
(holdout, Part B-D, Module B AIBOM) is deliberately not started.

---

# (history) Phase 3 PUBLISHED (live; GATE 2 FAIL disclosed)

## Publication complete (2026-11-08)

Published with owner-confirmed text; verifier frozen; no holdout data published.
- Code: <https://github.com/NagaYu/releaseseal> (Public, noreply author, LICENSE).
- Bench dataset: <https://huggingface.co/datasets/NagaYu/releaseseal-bench>
  (dev + dev_ext manifests, `audit/` with Part B v3 results + 3 evidence packs).
- Demo: <https://huggingface.co/spaces/NagaYu/releaseseal-demo> (Static Space,
  RUNNING; Part B table + working evidence-pack viewer).
- Entrance B done (dataset card links the live Space); Entrance A (community post)
  not done this run. Step-4 incident (approved card lacked the Space URL) was
  stopped-and-reported, then resolved with owner authorisation. Detail in
  `reports/phase3-publish.md`.
- Disclosed on the public artifacts: full gate history (GATE 1 PASS; GATE 2 FAIL
  ×3) and the V4 screening-signal limitation (final clean FP 82%).

---

# (history) Phase 3 prep done (export built; nothing pushed/posted)

## Phase 3 — publication prep (prep only)

Built the public export `~/Desktop/Claude code/ReleaseSeal-public/` (fresh repo,
to be a single clean noreply-authored commit): `src/` + rule packs (v1/v2/v3),
tests, dev/dev_ext bench, `docs/`, all reports, SPEC/DECISIONS/STATUS, an
English-lead `README.md`, `LICENSE` (All Rights Reserved + transfer), and HF prep
(`hf-dataset/`, `hf-audit/` with representative evidence packs, static
`hf-space/index.html`). Entrance note drafted (`reports/phase3-entrance-draft.md`).
See `reports/phase3-prep.md`.

- **Excluded & verified absent:** all holdout case data, `audit/` raw data,
  internal design doc. Only aggregate numbers (already in reports) are published.
- Verifier frozen at `73eef79`; tests unchanged (72 green, self-contained in the
  export). Wording discipline held: evidence, not certification.
- **Nothing pushed, uploaded, posted, or Space-created.** Publication execution
  (push / HF upload / Static Space / entrance post) awaits the owner's final
  confirmation in a separate run.

---

# (history) Phase 2 CLOSED (GATE 2 = FAIL, final; published as-is)

## GATE 2 final re-gate (holdout v3, scored once) — **FAIL**

- Scored `ModelPass-holdout-v3` (`cases_sha256` `22d4dd8a…901617395efc…491a`,
  84 cases) once with the frozen verifier `73eef79`; no tuning, no re-runs.
  Aggregates in `audit/holdout-v3/score.json` (no holdout cases in repo).
  (The instruction's quoted hash dropped one `9` in transcription → 63 chars; the
  folder's self-consistent 64-char manifest was confirmed authoritative and
  scored — see `reports/phase2-align.md` final section.)
- **Recall: V1–V7 all 1.000.** **Clean FP 0.821 (23/28).** Verdict **FAIL**
  (recall floor met everywhere; clean-FP ceiling exceeded). V3 multi-level 1.000
  (4/4 gp, 2/2 unknown, 2/2 direct).
- Cause: V4 **phrasing** false positives (energy 13, downstream 8, testing 7,
  training 7, compute 5) — the item-set mismatch is gone, but content-word
  patterns are finite and miss natural wording ("… MWh of electricity … tCO2e",
  "deploy behind an inference server", …). Not a recall failure.
- Predictions: recall vindicated (all 1.000 ≥ predicted); clean FP badly
  mis-predicted (predicted ≤10%, likely ≤5%; measured 82%) — right risk category,
  wrong magnitude. Detail in `reports/phase2-align.md`.
- **Stop rule in force:** third consecutive GATE 2 FAIL (always clean FP / V4);
  no further fix round, no fourth holdout; this FAIL is **published as-is**. The
  verifier stays frozen at `73eef79`. V1–V3/V5–V7 and the recursive-lineage work
  are strong; V4 documentation-presence is the honest, persistent limitation.
  Proceeds to the publication decision.

---

# (history) Phase 2 — re-gate FAIL; final alignment done; awaiting v3 re-gate

## Final alignment round (complete; verifier re-frozen; no scoring)

Addressed the re-gate FAIL at its roots (`reports/phase2-align.md`):
- **Item set single-sourced (D-25):** the active pack's 16 IDs are canonical;
  `docs/authoring-item-set.md` is generated from the pack, with a divergence test.
  Closes the compute/energy/downstream/acceptable-use item-set mismatch.
- **Content-word V4 matching (D-24, gpai-eu-v3, now default):** Porter-stemmed,
  windowed, order-independent co-occurrence replaces fixed phrases; fixes the
  "modalities"/"summary of training content"/"held-out test set" misses. v1/v2
  packs retained for reproducibility.
- **V6 value comparison (D-26):** prose vs structured values compared scale-aware.
- Validation (no tuning vs un-sealed holdouts): **GATE 1 held** (dev all 1.000,
  clean FP 0.000, dev `cases_sha256` unchanged; dev_ext walk 1.000); **72 tests
  green**. Holdout v2 regression: all phrasing trips cleared (170→108, residual is
  item-set only). Part B v1→v2→v3 doc_gap 376→297→281 (io_modality 34→7); V4
  occurrence still 40/40 (genuine Annex gaps). V6 recall on holdout v2 0.75→1.000.
- Pre-registered re-gate predictions: `reports/phase2-align-predictions.md`
  (clean FP 0–10%, likely PASS; residual risk = novel-phrasing V4 trips).
- **Final round:** the holdout-v3 re-gate result goes to the publication decision
  with no further fixes. Verifier re-frozen on this aligned state.

---

# (history) Phase 2 — GATE 2 = FAIL; re-gate also FAIL on clean FP

## GATE 2 re-gate (holdout v2, scored once) — **FAIL**

- Scored `ModelPass-holdout-v2` (`cases_sha256` `1419e1de…`, 84 cases) once with
  the frozen verifier `0ee34bf`; no tuning, no re-runs. Aggregates in
  `audit/holdout-v2/score.json` (no holdout cases in repo).
- Recall: V1–V5 **1.000**, V6 **0.750**, V7 **1.000**; **clean FP 1.000 (28/28)**.
  Verdict **FAIL** (V6 < 0.85; clean FP > 5%). V3 multi-level 1.000 (4/4 gp, 2/2
  unknown, 2/2 direct).
- Cause = **documentation-item-set mismatch**: the verifier gate-counts
  `xi.compute` + `xi.energy` (Annex XI 2(d)/(e)), which the holdout authoring item
  spec does not list → every clean card flagged on those two (28/28 each), plus
  residual phrasing misses on in-spec items. V6 0.750: 2 natural-sentence claims
  unparsed. Detail + vs-predictions in `reports/phase2-fix.md` "GATE 2 re-gate".
- The fixes improved recall vs the original GATE 2 (V5 0.75→1.0, V6 0.50→0.75,
  V7 0.875→1.0); D-23 held (V2 recall 1.0, no V2 clean FP). The blocker is now the
  item-set/phrasing V4 coverage, not a fix regression. Original GATE 2 = FAIL in
  `reports/phase2.md` unchanged.


Public name **ReleaseSeal** (was codename "ModelPass" through Phase 1; renamed in
Phase 2 per D-13 — history kept below). Local-only, $0, deterministic. Part B uses
the HF API for metadata only (no weights).

## Fix round (post-GATE-2, complete; verifier re-frozen; no re-scoring done)

- Applied D-17/D-18 heuristic fixes + the completion round D-20/D-21/D-22, then
  the D-23 correction.
- **FFN estimate (D-21 → corrected by D-23):** FFN structure is chosen by
  `model_type`; the clean V2 FPs were gated-MLP misestimation, NOT tied
  embeddings (D-18/D-19 corrected). **D-23:** `gpt_neox` is a *plain* MLP in
  reality, so it was removed from the gated set — the verifier models the real
  architecture, not the v1 author's convention.
- Rule-pack discipline restored: `gpai-eu-v1` back to 1.0.0; broadened rules ship
  as `gpai-eu-v2` (2.0.0), now the default (D-20). Provider-doc items need a
  substantive phrase or a reference field (D-22).
- Validation (no tuning vs the un-sealed holdout): **GATE 1 held** (dev recall all
  1.000, clean FP 0.000, dev `cases_sha256` unchanged; dev_ext walk 1.000);
  **67 tests green**. Holdout v1 regression: V5 0.75→1.000, V6 0.50→0.75,
  V7 0.875→1.000; V2 clean FP **0 → 2** after D-23 (the two v1 `gpt_neox` clean
  cards state a *gated* count for a plain-MLP arch — an author convention
  deviation, not a verifier bug). Part B v1→v2: doc_gap 376→297, V2 20→16, V6
  10→5, V7 1→0, context 3→0.
- Records: `reports/phase2-fix.md` (+ D-23 addendum), `reports/partb-v2.md`,
  `partb.md` Errata, DECISIONS D-20/D-21/D-22/D-23 + D-18/D-19 correction, re-gate
  predictions pre-registered (`reports/phase2-fix-predictions.md` + D-23 addendum).
- Re-gate pending: canonical set `ModelPass-holdout-v2` + scoring instructions to
  come. `ModelPass-holdout-2` is retired. Verifier **re-frozen** in this state.
  Dominant known risk: `cop.distribution` is gate-counted but not in the authoring
  item spec (see predictions).

## Phase 2 progress

- [x] Step 0 — rename ModelPass → ReleaseSeal (D-13); bench byte-identical verified
- [x] Step 1 — closed all four Phase-1 audit notes: recursive lineage (depth 8 +
      cycle guard), `dev_ext` + lineage-walk accuracy, real HF fixtures, per-class
      negatives, V8 `known_bases` seeded (D-14..D-16)
- [x] Step 2 — predictions pre-registered & git-locked before Part B (`reports/phase2-predictions.md`)
- [x] Step 3 — Part B: froze `bench/partb/models.json` (40 models), audited all,
      evidence packs in `audit/partb/` → `reports/partb.md`
- [x] Step 4 — holdout delivered & **scored once** with the frozen verifier
- [x] Step 5 — GATE 2 self-assessment → `reports/phase2.md`

## GATE 2 — **FAIL**

- Sealed independent holdout (84 cases, `cases_sha256` `2dd678fd…`) scored once,
  frozen verifier, D-17 fixes held. Recall: V1–V4 **1.000**, V5 **0.750**,
  V6 **0.500**, V7 **0.875**; **clean FP 1.000 (28/28)**. Criterion (recall ≥0.85
  all, FP ≤5%): **FAIL**. V3 multi-level recall 1.000 across all subtypes.
- Cause = overfitting the independent holdout exposed: V4 keyword brittleness
  (100% clean FP), V6 natural-sentence claims unparsed, V5 `result_files` source
  unread, V7 template-file reference missed, + 2 tied-embedding V2 FPs (D-17 #1).
  Details & vs-predictions in `reports/phase2.md` §1/§4; decision D-18.
- Part B (40 real models, 0 errors): V4 occurrence **100%** (real Annex gaps);
  V2 50% and V6/V7 small (mostly heuristic false positives — D-17); V3 0%.
- `dev_ext`: V3 recall 1.000, clean FP 0.000, **lineage-walk accuracy 1.000**.
- Tests: **52 passed**, offline. Frozen dev `cases_sha256` unchanged; verifier
  untouched after scoring.

## Known weaknesses (fix before any gate re-attempt / Phase 3)

Top blocker: **V4 keyword matching is phrasing-brittle** (D-18 → 100% clean FP).
Also V6 prose parsing, V5 `result_files`, V7 template-file (D-18), and the D-17
set (tied-embedding param estimate, claim extraction, `rope_theta`, V6 breadth,
`spm.model`). A gate re-attempt needs a **fresh** independent holdout (this one is
now un-sealed by scoring).

---

## Phase 1 history (GATE 1 PASS) — kept as record

Codename "ModelPass". **Phase 1 complete; GATE 1 PASS.**

### Progress

- [x] Step 1 — repo skeleton, pyproject, SPEC.md, DECISIONS.md, STATUS.md, git init
- [x] Step 2 — snapshot layer (schema, `local` + `hf` adapters, fixtures)
- [x] Step 3 — rule packs (`hub-metadata-v1`, `gpai-eu-v1`, `license-terms-v1`, `fingerprints-v1`)
- [x] Step 4 — verification core V1–V8 (V1–V7 deterministic, V8 signal-only)
- [x] Step 5 — evidence pack, verify-pack, report, `docs/bom-mapping.md`
- [x] Step 6 — bench Part A generator + scorer + CLI
- [x] Step 7 — tests (35 passing, offline)
- [x] Step 8 — GATE 1 self-assessment → `reports/phase1.md`

## GATE 1

- V1–V7 per-class recall: all **1.000** (12/12 each). Clean FP: **0.000** (0/36).
- Full test suite: **35 passed**, no network, no weight downloads.
- **GATE 1: PASS** (recall ≥ 0.90 all classes; FP ≤ 5%). Also passes seeds 1/2/7/42/123.
- Caveat: dev split is mutually-consistent with the rules that score it; real
  generalisation is a Phase-2 (holdout + Part B) question. See `reports/phase1.md`.

## Open items for Phase 2

- Name collision (design §0) still open; codename confined per DECISIONS.md D-01.
- Live HF fixtures (D-11), recursive ancestor-license resolution (D-12),
  populate `fingerprints-v1.known_bases`, Part B real-release audit, sealed holdout.

## Hard rules held

- Verifies consistency only; no "certificate" wording in any output.
- No weight-byte downloads; metadata + small files only. $0 spend. Tests offline.
- V8 is a labelled heuristic signal, never a gate input.
