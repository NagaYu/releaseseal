# ReleaseSeal — Part B v2 (fixed-verifier re-run)

**Not a compliance certification** (same discipline as `partb.md`).

Same frozen 40-model list (`bench/partb/models.json`, pinned revisions), re-snapshotted 2026-11-08 and verified with the **fixed** verifier (gpai-eu-v2 default; D-19/D-20/D-21/D-22). Metadata only, no weights. 40/40 snapshotted, 0 errors, 0 zero-finding. v1 numbers (frozen code + gpai-eu-v1 1.0.0) shown beside for comparison; the original GATE 2 = FAIL in `reports/phase2.md` is unchanged.

## Occurrence (models with ≥1 gate-counted finding of the class)

| class | v1 | v2 |
|---|---|---|
| V1 | 0 | 0 |
| V2 | 20 | 16 |
| V3 | 0 | 0 |
| V4 | 40 | 40 |
| V5 | 0 | 0 |
| V6 | 6 | 5 |
| V7 | 1 | 0 |

Finding-code totals: v1 = `doc_gap`×376, `param_mismatch`×18, `unsourced_claim`×10, `context_mismatch`×3, `tokenizer_missing`×1.

v2 = `doc_gap`×297, `param_mismatch`×16, `unsourced_claim`×5.

## Per-item V4 gaps across 40 models (v1 → v2)

| Annex/CoP item | v1 | v2 | note |
|---|---|---|---|
| cop.copyright_policy | 40 | 40 | genuinely absent on real cards (Art.53(1)(c)) |
| cop.distribution | 37 | 18 | synonyms (available on/hub/repository); still partly real |
| cop.training_content_summary | 40 | 40 | genuinely absent (Art.53(1)(d)) |
| xi.architecture | 1 | 0 |  |
| xi.compute | 38 | 38 | genuinely absent on most cards |
| xi.data_summary | 8 | 8 |  |
| xi.energy | 33 | 33 | genuinely absent on most cards |
| xi.evaluation_results | 18 | 16 |  |
| xi.intended_use | 16 | 13 | synonyms (intended for/use cases) |
| xi.testing_process | 37 | 36 | mostly genuinely absent |
| xi.training_process | 13 | 0 | synonyms (pretrained/fine-tuned) |
| xii.acceptable_use | 16 | 10 | synonyms (limitations/restrictions) |
| xii.downstream_integration | 40 | 11 | phrasing-robust synonyms (integrate/load/deploy) |
| xii.io_modality | 39 | 34 | depluralised (inputs and outputs) |
| **total doc_gap** | **376** | **297** | |

## Reading

- **V4 doc_gap 376 → 297.** The drop is phrasing-driven false gaps removed by gpai-eu-v2 (downstream-integration 40→11, distribution 37→18, training-process 13→0, io-modality 39→34). What **remains is the genuine EU-AI-Act signal**: a copyright policy (40/40) and a public training-content summary (40/40) are absent from every audited card, and training compute (38) and energy (33) from most — real gaps, with a card-field evidence pointer each. V4 occurrence stays 40/40 because every real card genuinely lacks at least one Annex item.
- **V2 20 → 16 models.** context_mismatch 3→0 (rope_theta, D-17 #3) and the gpt2/opt tied-embedding and t5 image-URL-hash false positives are gone. The **remaining 16 are a still-open weakness**: FAMILY cards that list the whole suite's sizes in a parameter context ("72 billion parameters", "175B", "34B model") — the extractor grabs a *sibling* model's size, not this model's — plus encoder-model estimate artifacts (deberta). Not real inconsistencies; recorded as a remaining weakness.
- **V6 unsourced 10 → 5** (hyperparameters/training-curve values excluded, D-17 #4). **V7 tokenizer_missing 1 → 0** (spm.model recognised, D-17 #5).
- **V1, V3, V5 remain 0** on this set (little declared lineage; no artifact/record or staleness drift surfaced).
- Gated-family note (D-21): adding gpt_neox as gated did not introduce new V2 FPs here (pythia's V2 is the family-card extraction issue, not the FFN estimate).
