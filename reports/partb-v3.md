# ReleaseSeal — Part B v3 (aligned-verifier re-run)

**Not a compliance certification** (same discipline as `partb.md`).

Same frozen 40-model list, re-snapshotted 2026-11-08 and verified with the **aligned** verifier (gpai-eu-v3: content-word matching D-24, 16-item single source D-25, V6 value comparison D-26; gpt_neox plain D-23). Metadata only. 40/40 ok, 0 errors, 0 zero-finding. v1 (gpai-eu-v1 1.0.0) and v2 (gpai-eu-v2 2.0.0) shown for comparison; the original GATE 2 / re-gate verdicts are unchanged.

## Occurrence (models with ≥1 gate-counted finding)

| class | v1 | v2 | v3 |
|---|---|---|---|
| V1 | 0 | 0 | 0 |
| V2 | 20 | 16 | 16 |
| V3 | 0 | 0 | 0 |
| V4 | 40 | 40 | 40 |
| V5 | 0 | 0 | 0 |
| V6 | 6 | 5 | 5 |
| V7 | 1 | 0 | 0 |

Code totals v3: `doc_gap`×281, `param_mismatch`×16, `unsourced_claim`×5.

## Per-item V4 gaps across 40 models (v1 → v2 → v3)

| item | v1 | v2 | v3 | note |
|---|---|---|---|---|
| cop.copyright_policy | 40 | 40 | 40 | genuinely absent (Art.53(1)(c)) |
| cop.distribution | 37 | 18 | 26 | stricter/more precise than v2 keywords (18→26) |
| cop.training_content_summary | 40 | 40 | 38 | genuinely absent (Art.53(1)(d)) |
| xi.architecture | 1 | 0 | 0 |  |
| xi.compute | 38 | 38 | 34 | genuinely absent on most cards |
| xi.data_summary | 8 | 8 | 6 |  |
| xi.energy | 33 | 33 | 33 | genuinely absent on most cards |
| xi.evaluation_results | 18 | 16 | 14 |  |
| xi.intended_use | 16 | 13 | 13 |  |
| xi.testing_process | 37 | 36 | 30 | more natural eval-process wording recognised |
| xi.training_process | 13 | 0 | 0 |  |
| xii.acceptable_use | 16 | 10 | 21 | stricter than v2 keywords (10→21) |
| xii.downstream_integration | 40 | 11 | 19 | stricter than v2 keywords (11→19) |
| xii.io_modality | 39 | 34 | 7 | content-word matching recognises real I/O descriptions (34→7) |
| **total doc_gap** | **376** | **297** | **281** | |

## Reading

- **V4 doc_gap 376 → 297 → 281.** Content-word matching (v3) most visibly fixes `io_modality` (34→7 — real cards describe inputs/outputs in prose the fixed phrases missed) and trims testing/compute/data/evaluation/training-summary. A few items rose vs v2 (`cop.distribution` 18→26, `acceptable_use` 10→21, `downstream` 11→19) because v2's broad keywords over-satisfied them; v3's content-word requirement is more precise. **V4 occurrence stays 40/40**: every real card genuinely lacks a copyright policy (40), a training-content summary (38), and usually compute (34) / energy (33) — the robust, genuine EU-AI-Act signal.
- **V2 16 models (unchanged from v2).** The remaining param_mismatch are **family cards** listing a suite's sizes ("72 billion parameters", "175B"), where the extractor grabs a sibling's size — a known, still-open weakness (not real inconsistencies). D-23 (gpt_neox plain) introduced no new V2 FPs.
- **V6 5** (unsourced prose claims); **V7 0**; **V1/V3/V5 0** (little declared lineage; no artifact/record or staleness drift).
- The aligned verifier is not more lenient overall — net doc_gap fell only 297→281 — it is more **accurate**: phrasing false gaps removed, genuine gaps kept, loose keyword satisfactions tightened.
