# ReleaseSeal — final alignment round report

Date 2026-11-08. Addresses the GATE 2 re-gate FAIL (holdout v2) at its two root
causes — a documentation item-set mismatch and brittle fixed-phrase matching —
plus the V6 value-comparison gap. **This is the final alignment round:** the
holdout-v3 re-gate result, whatever it is, proceeds to the publication decision
without further fixes. No scoring is done here. The prior verdicts
(`reports/phase2.md` GATE 2 = FAIL; `reports/phase2-fix.md` re-gate = FAIL) are
unchanged; corrections are appended as Errata only.

## Step 0 — Errata (recorded in `phase2-fix.md`)
Corrected three points in the re-gate section: the V6 miss was a *value-comparison
gap* (prose parsed, but benchmarks in structured records were never value-checked),
`xii.downstream_integration` was **not** in the authoring brief (so its trips are
item-set, not phrasing), and clean FP is **not** explained by compute/energy alone
— item-set and in-spec phrasing each account for ~half of the 170 v2 clean trips.

## Step 1 — Single-source the 16-item set (D-25)
The 16 item IDs in the active gpai pack are the single source of truth.
`docs/authoring-item-set.md` is **generated** from the pack
(`rules.render_authoring_item_set_md`); future authoring briefs are built from it;
and `test_authoring_item_set_in_sync_with_pack` fails if the file and the pack
diverge. This closes the compute / energy / downstream-integration /
acceptable-use mismatch that drove ~half the v2 clean FP.

## Step 2 — Content-word V4 matching, not more synonyms (D-24, gpai-eu-v3)
Replaced fixed-phrase/substring matching with **content-word co-occurrence**:
proper Porter stemming (so "modalities" → "modal", not a naive "modalitie"),
function words ignored, and each item satisfied when a pattern's content words
co-occur order-independently **within one sentence window**. Patterns are sourced
from Annex wording, dev sentences, the disclosed holdout v1/v2 cards, and the
Part B real cards (per-item rationale in DECISIONS D-24). Default pack → v3; v1
(1.0.0) and v2 (2.0.0) kept for reproducibility.

## Step 3 — V6 value comparison (D-26)
A prose claim whose benchmark also appears in a structured record now has its
**value** compared on a common 0–100 scale (a value ≤ 1 read as a fraction ×100);
a disagreement > 2.0 fires `eval_value_mismatch`, a scale-only agreement is
silent, and a benchmark with no structured source stays `unsourced_claim`.
Both-direction tests added.

## Step 4 — Regression & Part B v3

### dev / dev_ext — unchanged (GATE 1 intact)
dev per-class recall all **1.000**, clean FP **0.000**, `cases_sha256` `5267e1a0…`
unchanged; dev_ext lineage-walk **1.000**. dev covers all 16 items, so clean FP 0
confirms the content-word matcher satisfies a complete card. **72 tests green.**

### Disclosed holdout regression (v2 pack → v3 pack; regression data, not a gate)
Clean V4 trips (28 clean cards each):

| set | v2-pack total | v3-pack total | what changed |
|---|---|---|---|
| holdout v1 | 56 (testing 28, distribution 28) | 56 (testing 28, distribution 28) | unchanged — v1 cards genuinely lack testing-process & distribution content (v1's narrower spec); not phrasing |
| holdout v2 | 170 | 108 | **all phrasing misses cleared** (testing 23→0, io 17→0, data 15→0, intended-use 10→0, training-content-summary 7→0, training 4→0); residual is the item-set gap only (compute 28, energy 28, downstream 28, acceptable-use 24) |

Both still show 100% clean FP because v1/v2 were authored to narrower item specs
(10 items) than the verifier's 16 — exactly the mismatch Step 1 fixes for v3.
Content-word matching removed every v2 **phrasing** trip; nothing phrasing-driven
remains.

### Part B v3 (`reports/partb-v3.md`)
40 real models, 0 errors. V4 doc_gap **376 → 297 → 281**; the visible win is
`io_modality` 34→7 (real cards' I/O prose now recognised). Occurrence stays 40/40
(genuine Annex gaps: copyright 40, training-content summary 38, compute 34, energy
33). V2 16 (family-card extraction, unchanged), V6 5, V7 0. The aligned verifier is
not more lenient (281 vs 297) — it is more **accurate**: phrasing false gaps
removed, genuine gaps kept, loose keyword satisfactions tightened.

## Step 5 — Pre-registered predictions
`reports/phase2-align-predictions.md` committed before holdout v3 exists:
predicted recall ≥ 0.90 for most classes and **clean FP 0–10% (likely ≤5%)**, with
the one residual risk being V4 clean trips from natural phrasings outside the
content-word patterns. Overall call: more likely PASS than FAIL; any FAIL expected
to be a small V4 clean-FP overage, not the systematic 100% of v2.

## Remaining weaknesses (honest)
1. **Content-word patterns are finite** — a novel phrasing for one item can still
   be missed → the main residual clean-FP risk (why the prediction is not 0%).
2. **Family-card parameter extraction** (Part B V2, 16 models) — unchanged; a
   recall-side real-data issue, not a holdout clean-FP issue.
3. **V6 prose extraction** still needs a parseable "<score> on <benchmark>" form.
4. **Encoder models** — the decoder param estimate is wrong for encoder/enc-dec
   (out of the GPAI decoder-LM target, but present in Part B).

## Status
Steps 0–5 complete; GATE 1 held (dev/dev_ext unchanged); 72 tests green; verifier
re-frozen on the aligned state. **This is the final alignment round** — the
holdout-v3 re-gate (authored from `docs/authoring-item-set.md`, scored once with
this frozen verifier) is decisive, and its result goes to the publication decision
with no further fixes. Scoring not yet performed.

---

## GATE 2 — FINAL re-gate (holdout v3, scored once)

Scored the designated holdout `ModelPass-holdout-v3` **exactly once** with the
frozen verifier at align commit `73eef79` (working tree clean; no tuning, no
re-runs). Aggregates only in `audit/holdout-v3/score.json`; no holdout cases in
the repo.

**Hash / transcription incident.** The scoring instruction quoted
`cases_sha256 …90161735efc…` (63 characters — a transcription that dropped one
`9`). The holdout folder's manifest is self-consistent at the 64-character
`22d4dd8a5fcd0f7b7674244c901617395efc0734238ad0958e534b1df851491a`, which is the
value delivered when v3 was authored. Per the stop-and-report rule I did not
score on the mismatch; the owner confirmed the 64-char value as authoritative,
and that set was scored.

| class | recall | | class | recall |
|---|---|---|---|---|
| V1 | **1.000** (8/8) | | V5 | **1.000** (8/8) |
| V2 | **1.000** (8/8) | | V6 | **1.000** (8/8) |
| V3 | **1.000** (8/8) | | V7 | **1.000** (8/8) |
| V4 | **1.000** (8/8) | | **clean FP** | **0.821 (23/28)** |

**Verdict: FAIL** — every V1–V7 recall ≥ 0.85 is **met** (all 1.000), but clean FP
**0.821** exceeds the ≤ 0.05 ceiling. V3 multi-level recall 1.000 (4/4
grandparent-only, 2/2 unknown-intermediate, 2/2 direct).

### Clean FP decomposition (V4 only; 40 trips across 23 cards)

| item | clean cards flagged |
|---|---|
| `xi.energy` | 13 |
| `xii.downstream_integration` | 8 |
| `xi.testing_process` | 7 |
| `xi.training_process` | 7 |
| `xi.compute` | 5 |

All are **phrasing** misses, not an item-set mismatch (the 16-item single-source
closed that — compute/energy/downstream were documented in every clean card).
The content-word patterns, though order-independent and stemmed, remain **finite**
and did not anticipate the full range of natural wording: e.g. energy stated as
"… MWh of electricity … tCO2e" / "… emitted" (no "energy consumption" / "carbon
emission" content pair), downstream as "deploy behind an inference server", and
training/testing described without the pattern's content words. Roughly half the
cards used an energy phrasing outside the patterns, hence energy 13/28.

### Comparison with pre-registered predictions (`reports/phase2-align-predictions.md`)

- **Recall: vindicated and exceeded.** Predicted 0.85–1.00 per class; measured
  **1.000 on all seven** (V6 value comparison, D-23 plain gpt_neox, recursive
  lineage all held; param convention matched).
- **Clean FP: badly mis-predicted.** Predicted **0–10% (likely ≤ 5%)**; measured
  **82%**. The prediction named the correct *category* ("V4 clean trips from
  natural phrasings outside the content-word patterns — the main residual
  clean-FP risk, the reason I do not predict 0%") but **drastically
  under-estimated its magnitude** ("a handful of trips at most … a small clean-FP
  overage, not the systematic 100% of v2"). The honest finding: content-word
  matching reduced but did **not** solve V4 phrasing brittleness — a finite
  pattern set cannot cover the open space of natural wording for every Annex item.

### Verdict and stop rule

GATE 2 is **FAIL** on this third, independent set — the third consecutive GATE 2
FAIL (original, and both re-gates), each on clean FP driven by V4. Recall and the
lineage machinery are strong and improving; the V4 documentation-presence check is
the persistent blocker. Per the recorded stop rule, **this is the final round:
no further fix round and no fourth holdout; this FAIL is published as-is.** The
original `reports/phase2.md` and `reports/phase2-fix.md` verdicts are unchanged.
