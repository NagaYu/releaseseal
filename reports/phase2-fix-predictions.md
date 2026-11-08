# ReleaseSeal — re-gate (post-fix) pre-registered predictions

Written and committed **before** the canonical re-gate holdout (`ModelPass-holdout-v2`,
to be authored independently) exists or is scored. Not edited afterward;
corrections may only be **appended** (dated). These predict the re-gate of the
**fixed** verifier (gpai-eu-v2 default; D-19/D-20/D-21/D-22 fixes) against a fresh
independent holdout authored to the same item spec as the prior rounds.

GATE 2 criterion (unchanged): per-class recall ≥ 0.85 for every V1–V7 **and**
clean FP ≤ 5%.

## Predicted per-class recall

| class | predicted recall | reasoning |
|---|---|---|
| V1 | 0.90–1.00 | artifact/record checks are structural and robust. |
| V2 | 0.85–1.00 | param (gated/tied range), architecture, context (rope_theta), relation all solid; risk if the author's own param convention differs from the verifier's family MLP map (D-21). |
| V3 | 0.90–1.00 | recursive lineage + multi-level proven on dev_ext and holdout v1 (1.000). |
| V4 | 0.80–0.97 | v2 phrasing-robust (synonyms + normalisation + depluralisation); residual risk from item phrasings outside the synonym set. |
| V5 | 0.88–1.00 | now also reads `result_files` source checkpoints (D-18 #8). |
| V6 | 0.80–0.95 | natural-sentence claims now parsed and hyperparameters excluded; prose extraction remains heuristic, so unusual phrasings may still be missed. |
| V7 | 0.88–1.00 | spm.model + chat-template-file now covered. |

## Predicted clean FP

**0–15%, but with a specific, dominant risk I am flagging now:** the item spec
given to holdout authors enumerates "testing/evaluation process" (so a competent
author covers it) but does **not** enumerate **distribution channels**, which the
v2 pack still gate-counts (`cop.distribution`). On holdout v1 this produced a
clean-FP on every card via `cop.distribution` (and `xi.testing_process`, which v1
authors omitted). If the re-gate author likewise omits a distribution statement,
clean FP could spike toward 100% on that single item alone — a measurement
artifact of a **spec/pack mismatch**, not a phrasing bug.

- If the re-gate clean cards cover every v2-pack item (including a distribution
  statement, naturally phrased e.g. "available on the Hub"): **clean FP 0–8%**.
- If they omit distribution (following the item spec literally): **clean FP high
  (up to ~90%+)** on `cop.distribution`.

Recommendation (for the separate scoring round): either the re-gate authoring
brief should enumerate distribution channels among the required items, or
`cop.distribution` should be satisfiable structurally (the source repo *is* the
distribution channel) / demoted from the gate. This is surfaced, not resolved
here, to avoid tuning the verifier to any specific holdout.

## Known remaining weaknesses carried into the re-gate

1. **Gated-family over-count risk (D-21):** a genuinely plain-MLP model whose
   `model_type` is in the gated set would be over-estimated → a possible clean V2
   false positive. The audit directed adding `gpt_neox`; real GPTNeoX MLPs are
   plain, so this is a deliberate convention with a V2-direction risk.
2. **Distribution item spec/pack mismatch** (above) — the largest clean-FP risk.
3. **V6 prose extraction is heuristic** — recall risk on unusually-phrased claims.
4. **Param-claim extraction now requires an explicit parameter context** — may
   miss a claim a holdout plants with unusual wording (V2 recall risk, not FP).

## Overall call

If the re-gate clean cards cover distribution, I predict **GATE 2 PASS** (all
recalls ≥ 0.85, clean FP ≤ 5%). If they do not, I predict **FAIL on clean FP**
driven solely by `cop.distribution` — which would indicate the spec/pack
alignment issue above, not a regression in the fixes.

---

## Addendum (D-23, appended; original predictions above unchanged)

After these predictions were committed, D-23 reverted `gpt_neox` to a plain MLP
(it is not gated in reality). These predictions were written **with this risk
explicit** — see "Known remaining weaknesses" #1 ("Gated-family over-count
risk … the audit directed adding `gpt_neox`; real GPTNeoX MLPs are plain, so this
is a deliberate convention with a V2-direction risk"). D-23 **removes** that
risk at the source.

Effect on the predicted numbers: **V2 recall and clean-FP predictions are
unchanged or slightly improved.** The reverted estimate is now correct for real
NeoX models, so a competent re-gate author stating a NeoX model's true (plain)
parameter count would no longer be falsely flagged — eliminating one predicted
clean-FP source rather than adding one. Known-weakness #1 is downgraded from a
live risk to resolved; the dominant clean-FP risk remains the `cop.distribution`
spec/pack mismatch (unchanged). No other predicted value changes.
