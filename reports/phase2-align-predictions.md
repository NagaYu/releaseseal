# ReleaseSeal — holdout v3 re-gate pre-registered predictions

Written and committed **before** the canonical re-gate holdout `ModelPass-holdout-v3`
exists or is scored. Not edited afterward; corrections may only be **appended**
(dated). Predicts the re-gate of the aligned verifier (gpai-eu-v3 default,
content-word matching D-24; 16-item single source D-25; V6 value comparison D-26;
gpt_neox plain D-23) against a fresh independent holdout authored from
`docs/authoring-item-set.md` (all 16 items).

GATE 2 bars (unchanged): per-class recall ≥ 0.85 for every V1–V7 **and** clean
FP ≤ 5%.

## What the alignment changed (basis for these predictions)

- **Item-set mismatch resolved.** The v2 re-gate FAIL was ~half an item-set
  mismatch (compute, energy, downstream-integration, acceptable-use were
  gate-counted but not in the brief). v3 briefs are generated from the 16-item
  pack, so a competent author documents all 16 — removing that entire clean-FP
  source. (On dev, which covers all 16 items, clean FP is 0.)
- **Phrasing misses resolved.** Content-word (stemmed, windowed, order-free)
  matching cleared every holdout-v2 in-spec phrasing miss (testing 23→0, io 17→0,
  data 15→0, intended-use 10→0, training-content-summary 7→0, training 4→0) and
  the three audit examples ("modalities", "a summary of the training content",
  "validated … held-out test set") now match.
- **V6** now compares prose values to structured records (scale-aware), so the
  two prior V6 misses are fixed (holdout v2 V6 recall 0.75 → 1.000 under v3).

## Predicted per-class recall

| class | predicted | reasoning |
|---|---|---|
| V1 | 0.90–1.00 | structural checks, robust. |
| V2 | 0.85–1.00 | param (plain gpt_neox, D-23), arch, context, relation solid; holdout authors state accurate counts, so the family-card extraction weakness (a Part B issue) does not bite here. |
| V3 | 0.95–1.00 | recursive lineage proven on dev_ext + v1 + v2 (1.000). |
| V4 | 0.90–1.00 | content-word patterns catch inflected/reordered wording; a dropped item is still detected (dev V4 recall 1.000). |
| V5 | 0.90–1.00 | card/model-index/result-file drift + stale dates all covered. |
| V6 | 0.90–1.00 | value comparison added (dev + holdout v2 now 1.000). |
| V7 | 0.90–1.00 | tokenizer/template-file/weightmap/genconfig covered. |

## Predicted clean FP

**0–10%.** The two systematic causes of the v2 100% are removed (item-set gap via
single-sourcing; phrasing via content-word matching). The residual risk is a
genuinely novel phrasing for some one item on some card that falls outside every
content-word pattern — content-word matching is broad but still finite. I expect
a handful of such trips at most, so **≤ ~10%, most likely ≤ 5%**.

## Known residual weaknesses carried in

1. **Content-word patterns are finite.** An author could describe an item with
   content words none of the patterns list (e.g. an idiom) → a V4 clean trip. This
   is the main clean-FP risk, and the reason I do not predict 0%.
2. **Family-card parameter extraction** (Part B) is unchanged — a recall-side
   Part B issue, not a holdout clean-FP issue (holdout authors state the model's
   own count).
3. **V6 prose extraction** still depends on the claim being parseable as
   "<score> on <benchmark>" or "<benchmark>: <score>".
4. **gpt_neox plain (D-23)**: a holdout author using a gated-family `model_type`
   with a *plain* MLP count (non-standard) could trip V2 — unlikely from a
   standard author.

## Overall call

I predict the v3 re-gate is **more likely PASS than FAIL** — all recalls ≥ 0.85
and clean FP ≤ 5% — with the single residual risk being V4 clean trips from
natural phrasings outside the content-word patterns. If it FAILS, I expect it to
be a **small** clean-FP overage on V4 (a few cards), not the systematic 100% of
v2, and not a recall failure. This is the final alignment round: the v3 re-gate
result, whatever it is, goes to the publication decision without further fixes.
