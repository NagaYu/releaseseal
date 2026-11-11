# Part B-D — real dataset audit (36 frozen Hugging Face datasets)

Companion to the model-side `hf-audit/partb-v3-results.md`. Written from
`hf-dataset/partbd-summary.json` (`partbd-summary/1`, captured 2026-11-11); every number
here is reproduced from that file, no cherry-picking — all 36 datasets are listed.

> **Evidence, not certification.** These are consistency/measurement findings over
> a pinned snapshot at a stated sampling coverage. The pack **never certifies
> absence** of PII, contamination, or duplication; a finding is a place to check.

## What this audit is

A live, metadata-and-sample audit of **36** popular public HF datasets, frozen by
rule (`bench/partbd/datasets.json`, committed before the run) then verified with the
frozen dataset verifier (`dataset-hub-v1` 1.1.0, `contamination-v1` 1.1.0, `lid-v1`
1.0.0, `license-terms-v1` 1.0.0). **36/36 ran, 0 errors, $0** — HF datasets-server
metadata plus a `dsample/1`-capped content sample (`rows_per_split=200`,
`max_splits=2`, largest row-served config); no bulk or weight downloads. Raw sample
text is never persisted; W4 values are masked on disk (see the shipped packs under
`packs-d/`).

## Headline — measurement, not falsification

The honest real-data result is a **measurement** result, not a claim-falsification
result:

- **W8 dataset-card completeness gaps: 100%** — every one of the 36 real cards is
  missing at least one machine-readable declaration field. This is the headline
  figure. (W8 is a signal, never a gate.)
- **Claim violations ≈ 0.** Real dataset cards carry almost none of the structured
  declarations the W-checks grade, so there is almost nothing to violate. Across all
  36 datasets the only `declared_language_absent` findings (321) come from **one**
  dataset, `wikimedia/wikipedia`, and are a **coverage limitation of this audit**,
  not a real falsification (see note² below) — they are **not** presented as
  violations.
- **Datasets with ≥1 counted finding (non-heuristic, non-info): 13 / 36.**
- **Content coverage is thin by nature:** 19 / 36 datasets yielded a content sample;
  17 / 36 returned an empty sample (image / audio / binary corpora, or configs
  datasets-server does not row-serve). Content findings therefore cover 19 datasets.

### Preregistered predictions (committed before the audit): 2 HIT / 4 MISS

| id | prediction | threshold | measured | verdict |
|---|---|:--:|:--:|:--:|
| P1 | ≥60% of datasets ≥1 counted finding | 0.60 | 0.361 (13/36) | MISS |
| P2 | W1 license inconsistency in ≥25% | 0.25 | 0.000 | MISS |
| P3 | W4 detector hits in ≥15% | 0.15 | **0.194 (7/36)** | **HIT** |
| P4 | W5 measured overlap >0 in ≥10% | 0.10 | 0.028 (1/36) | MISS |
| P5 | W7 declared-language problems in ≥10% | 0.10 | 0.028 (1/36) | MISS |
| P6 | W8 completeness gaps in ≥50% (signal) | 0.50 | **1.000** | **HIT** |

The predictions were optimistic in the same direction the model-side GATE 2 history
warned about. The disclosed reading: the module's real-data value is **measurement
at stated coverage**, not claim falsification.

## Detector / measurement detail (at sampled coverage)

- **W4 PII detectors** — format hits only, all values masked: **email 29, card_luhn
  9, ipv4 2** across **7** web-crawl corpora. The counted W4 rate is **0.194
  (7/36)**. The 9 `card_luhn` hits on web text are **Luhn-valid-by-chance digit
  strings, not confirmed card numbers** — a high-precision *format* match is not a
  confirmed card.
- **W5 benchmark overlap** — measured >0 on exactly **1** dataset: `openai/gsm8k`
  vs its own source suite `gsm8k-test` (0.502). Circular by construction (the suite
  is drawn from that dataset) but a correct measurement.
- **W6 dedup** — measured on all 19 content-sampled datasets (an audit fact, never
  gated unless a numeric declared dedup rate exists to compare — none did).
- **W1 license** — `license_inconsistent`: **0** across all 36. `license_unknown`
  (declared license outside the frozen 12-entry `license-terms-v1` table →
  "undeterminable", **never** an inferred verdict): **10** datasets.

## Per-dataset results — all 36 (no cherry-picking)

| # | dataset | declared license | family | sampled / total rows | counted | W1 | W4 detector hits (masked) | W5 overlap | W7 lang gaps | W6 dedup | claim viol. | lic?¹ |
|--:|---|---|---|---|--:|--:|---|---|--:|--:|--:|:--:|
| 1 | `ahnaftaz/locus-commit-pool-v1` | other | other_or_unknown | 0/— | 1 | 1 | — | — | 0 | — | 0 | yes |
| 2 | `allenai/ai2_arc` | cc-by-sa-4.0 | copyleft | 400/5,197 | 0 | 0 | — | — | 0 | 0.000 | 0 | — |
| 3 | `anon8231489123/ShareGPT_Vicuna_unfiltered` | apache-2.0 | permissive | 0/— | 0 | 0 | — | — | 0 | — | 0 | — |
| 4 | `applied-ai-018/pretraining_v1-omega_books` | — | other_or_unknown | 200/103,802,366 | 7 | 0 | email 7 | — | 0 | 0.000 | 0 | — |
| 5 | `ayuo/hd_tmp` | — | other_or_unknown | 0/— | 0 | 0 | — | — | 0 | — | 0 | — |
| 6 | `cais/mmlu` | mit | permissive | 400/115,700 | 0 | 0 | — | — | 0 | 0.010 | 0 | — |
| 7 | `carlotabronze/sm-stuff` | — | other_or_unknown | 0/— | 0 | 0 | — | — | 0 | — | 0 | — |
| 8 | `epfml/FineWeb-HQ` | odc-by | permissive | 200/2,445,786,576 | 6 | 1 | email 4, card_luhn 1 | — | 0 | 0.000 | 0 | yes |
| 9 | `hallucinations-leaderboard/requests` | apache-2.0 | permissive | 0/— | 0 | 0 | — | — | 0 | — | 0 | — |
| 10 | `hallucinations-leaderboard/results` | apache-2.0 | permissive | 0/— | 0 | 0 | — | — | 0 | — | 0 | — |
| 11 | `huggingface/DEH-image-scan-data` | — | other_or_unknown | 6/6 | 0 | 0 | — | — | 0 | 0.000 | 0 | — |
| 12 | `HuggingFaceFW/fineweb` | odc-by | permissive | 200/518,458,467 | 8 | 1 | ipv4 2, email 5 | — | 0 | 0.000 | 0 | yes |
| 13 | `HuggingFaceFW/fineweb-edu` | odc-by | permissive | 200/1,525,223,056 | 6 | 1 | email 4, card_luhn 1 | — | 0 | 0.000 | 0 | yes |
| 14 | `lerobot/FineART` | cc-by-4.0 | permissive | 0/— | 0 | 0 | — | — | 0 | — | 0 | — |
| 15 | `Lichess/standard-chess-games` | cc0-1.0 | permissive | 200/7,136,017,970 | 1 | 1 | — | — | 0 | 0.000 | 0 | yes |
| 16 | `m-a-p/FineFineWeb` | apache-2.0 | permissive | 0/1,646,140 | 0 | 0 | — | — | 0 | — | 0 | — |
| 17 | `mlfoundations/MINT-1T-HTML` | cc-by-4.0 | permissive | 200/897,871 | 14 | 0 | email 9, card_luhn 5 | — | 0 | 0.000 | 0 | — |
| 18 | `mvp-lab/LLaVA-OneVision-1.5-Mid-Training-85M` | apache-2.0 | permissive | 0/91,493,097 | 0 | 0 | — | — | 0 | — | 0 | — |
| 19 | `nicoboou/IDRCell100k` | — | other_or_unknown | 0/308,899 | 0 | 0 | — | — | 0 | — | 0 | — |
| 20 | `nyu-mll/glue` | other | other_or_unknown | 400/795,241 | 1 | 1 | — | — | 0 | 0.000 | 0 | yes |
| 21 | `open-cn-llm-leaderboard/requests` | apache-2.0 | permissive | 0/— | 0 | 0 | — | — | 0 | — | 0 | — |
| 22 | `open-index/hacker-news` | odc-by | permissive | 0/— | 1 | 1 | — | — | 0 | — | 0 | yes |
| 23 | `openai/gsm8k` | mit | permissive | 400/8,792 | 0 | 0 | — | gsm8k-test 0.502 | 0 | 0.000 | 0 | — |
| 24 | `OPR-Project/OxfordRobotCar_OpenPlaceRecognition` | cc-by-nc-sa-4.0 | non_commercial | 0/— | 0 | 0 | — | — | 0 | — | 0 | — |
| 25 | `pulmo/ncbi-genbank-complete` | apache-2.0 | permissive | 0/— | 0 | 0 | — | — | 0 | — | 0 | — |
| 26 | `roisincrtai/ptb-xl-1.0.3` | — | other_or_unknown | 200/87,858 | 0 | 0 | — | — | 0 | 0.000 | 0 | — |
| 27 | `ryanmarten/OpenThoughts-1k-sample` | — | other_or_unknown | 200/1,000 | 1 | 0 | card_luhn 1 | — | 0 | 0.000 | 0 | — |
| 28 | `Salesforce/GiftEvalPretrain` | apache-2.0 | permissive | 0/— | 0 | 0 | — | — | 0 | — | 0 | — |
| 29 | `Salesforce/wikitext` | cc-by-sa-3.0 | copyleft | 400/1,809,468 | 1 | 1 | — | — | 0 | 0.000 | 0 | yes |
| 30 | `ThomasTheMaker/ptb-xl-ecg` | — | other_or_unknown | 200/87,858 | 0 | 0 | — | — | 0 | 0.000 | 0 | — |
| 31 | `TIGER-Lab/MMLU-Pro` | mit | permissive | 270/12,102 | 0 | 0 | — | — | 0 | 0.000 | 0 | — |
| 32 | `uoft-cs/cifar10` | unknown | other_or_unknown | 400/60,000 | 1 | 1 | — | — | 0 | 0.000 | 0 | yes |
| 33 | `visionhdstream/data-vision-01` | — | other_or_unknown | 200/222 | 0 | 0 | — | — | 0 | 0.000 | 0 | — |
| 34 | `wikimedia/wikipedia` | cc-by-sa-3.0 | copyleft | 200/6,407,814 | 323 | 1 | card_luhn 1 | — | 321 | 0.000 | 321 | yes |
| 35 | `world-igr-plum/regions` | mit | permissive | 0/— | 0 | 0 | — | — | 0 | — | 0 | — |
| 36 | `xlangai/ubuntu_osworld_file_cache` | apache-2.0 | permissive | 0/— | 0 | 0 | — | — | 0 | — | 0 | — |

¹ `lic?` = W1 `license_unknown`: the declared license is outside the frozen 12-entry
`license-terms-v1` table, so it is reported *undeterminable* — never guessed
compatible or incompatible.

² **`wikimedia/wikipedia` W7 (321).** The card declares ~320 languages, but the
content sample came from a **single language config**, so every other declared
language measured 0 occurrences. This is a **sampling-coverage artifact of the audit
itself** — the dataset genuinely contains those languages in other configs — and is
the one clear coverage limitation this run surfaced. It is **not** a real
falsification and is **not** counted as a claim violation in the headline.
Multilingual cards sampled from one config over-fire `declared_language_absent`; the
fix is per-config sampling (a future snapshot), not a code bug.

## Reproduce

```bash
export PYTHONPATH=src
# frozen selection (committed before the audit):
cat bench/partbd/datasets.json
# the audit runner (live datasets-server metadata + capped sample; $0, no weights):
python3 bench/partbd/run_partbd.py        # writes audit/partbd/*.{snap,pack}.json + summary.json
```

The three packs in `packs-d/` (`openai__gsm8k`, `HuggingFaceFW__fineweb`,
`mlfoundations__MINT-1T-HTML`) are representative `pack/2` evidence packs with W4
values masked, re-verifiable offline with `releaseseal verify-pack`.
