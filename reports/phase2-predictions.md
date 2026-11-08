# ReleaseSeal — Phase 2 pre-registered predictions

Written **2026-11-08, before** `bench/partb/models.json` was frozen and before any
Part B snapshot was fetched or scored, and before any holdout exists. This file is
**not edited** after the fact; corrections may only be **appended** (dated).

These are blind priors from the Phase-1 design and the rule behaviour, recorded so
the Part B and holdout results can be judged against a commitment, not a
post-hoc story.

## Part B — predicted share of ~40 real models with ≥1 finding of each class

Occurrence = fraction of audited models that produce at least one **gate-counted
(V1–V7)** finding of that class. Ranges are my 1-sigma intervals.

| class | predicted occurrence | reasoning |
|---|---|---|
| V4 documentation gaps | **85–100%** | Real cards almost never cover every Annex XI/XII + CoP item (training-content summary, copyright policy, energy, compute are routinely absent). |
| V3 license lineage | **40–70%** | Many models declare `base_model`; gated ancestors (Llama/Gemma) return 401 on metadata fetch → `license_unknown`. Mostly undeterminable, some genuine `license_incompatible`. |
| V6 eval inconsistency | **20–45%** | Headline numbers in prose without structured `model-index`, and model-index/result-file drift, are common. |
| V7 release completeness | **10–30%** | Official base releases are usually loadable; gaps appear in hastily-published derivatives. |
| V1 artifact–record | **5–20%** | Safetensors indices are usually self-consistent; undocumented extra weights occasionally. |
| V2 architecture & scale | **5–20%** | Official param/context claims usually match config; mismatches are the exception. |
| V5 staleness / drift | **5–20%** | Explicit `as_of` dates are rare in cards; revision drift is occasional. |
| V8 undeclared derivation (signal, not gate-counted) | **<10%** | `known_bases` is a small seed (3 entries); few models will match and also declare no base. |

- **Most frequent class predicted: V4** (documentation gaps), by a wide margin.
- **Most surprising prediction:** V3's occurrence will be driven mostly by
  `license_unknown` from **gated ancestors** (Llama/Gemma 401s), i.e. an artifact
  of metadata-only auditing rather than real license violations. I expect genuine
  `license_incompatible` to be **rare (<10% of models)**. If instead many true
  incompatibilities surface, that is the surprising outcome.
- I expect **0 models with zero findings is unlikely** but possible; most models
  will have ≥1 finding, almost always including a V4 gap.

## Holdout — predicted per-class recall and clean FP

(If a sealed holdout is delivered; scored once with the frozen verifier.)

| class | predicted recall |
|---|---|
| V1 | 0.90–1.00 |
| V2 | 0.90–1.00 |
| V3 | 0.88–1.00 (multi-level cases may stress the walk) |
| V4 | **0.82–0.95** (keyword detection is the most phrasing-sensitive; likely the weakest) |
| V5 | 0.88–1.00 |
| V6 | **0.82–0.95** (prose unsourced-claim extraction is pattern-sensitive) |
| V7 | 0.90–1.00 |

- **Clean FP rate predicted: 0–8%** (target ≤5%). The risk is independently
  authored clean cards whose prose happens to miss a keyword or trip the prose
  claim regex.
- **Lineage-walk accuracy predicted: 0.80–1.00** on multi-level holdout cases.
- Overall I predict GATE 2 is **more likely PASS than FAIL**, with V4 and V6 the
  classes most at risk of dipping below the 0.85 floor.

## GATE 2 criteria (transcribed from the Phase 2 prompt)

> holdout のクラス別 recall が V1–V7 全て ≥ 0.85、かつ clean FP 率 ≤ 5%。

PASS iff holdout per-class recall ≥ 0.85 for every V1–V7 **and** clean FP ≤ 5%.
If no holdout is delivered, GATE 2 is **judgment-pending**; Part B still completes
and is reported in full.
