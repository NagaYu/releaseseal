# STATUS — Phase 3 prep done (export built; nothing pushed/posted)

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
