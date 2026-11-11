# Phase E2 (build half) — predictions, W1 file leg, real contamination suites, Part B-D audit

Scope: the **build** half of Phase E2 per the Phase-E2 build prompt and
`releaseseal-extension-design.md` §3. This session preregistered predictions,
switched on W1's LICENSE-file leg, added real benchmark suites to
`contamination-v1`, and ran the Part B-D real-dataset audit. **Out of scope here
(other sessions):** authoring the sealed holdout, scoring any holdout, and Module
B (AIBOM). Choices recorded as DECISIONS **D-37..D-41**. No publication, no remote
writes — local commits only.

**GATE E2: not judged in this session — awaiting sealed holdout + scoring
session.** This report records the build and the Part B-D audit; the gate verdict
is the later scoring session's, against the independently sealed holdout.

## 0. Predictions (preregistered, committed first)

`reports/phase-e2-predictions.md` was committed as its own commit (`f3b9cba`)
**before any E2 code change** (hard rule 1). It is unchanged since. The holdout
block is scored by the later session; the Part B-D block is scored below.

## 1. Step 1 — W1 LICENSE-file identification leg (live)

- `dataset-hub-v1` bumped **1.0.0 → 1.1.0**, adding `license_file_phrases`
  (per id: `required` — ALL present — and `forbidden` — NONE present) and
  `license_file_order` (pinned evaluation order, `lgpl-3.0-only` before
  `gpl-3.0-only`, `cc-by-nc-4.0` before `cc-by-4.0`). `license-terms-v1` stays
  **byte-unchanged** (D-29 constraint holds; identification data lives in
  `dataset-hub-v1` — D-37). Normalization pinned (SPEC §E1.3 + the pack):
  lowercase → drop any line containing `copyright`/`(c)` → collapse whitespace →
  strip; phrases match as substrings. Covered ids: `apache-2.0`, `mit`,
  `bsd-3-clause`, `cc-by-4.0`, `cc-by-nc-4.0`, `cc0-1.0`, `gpl-3.0-only`,
  `lgpl-3.0-only`, `mpl-2.0`.
- LICENSE text reaches the check through a new **optional** `dsnapshot/1` field
  `license_files` (`{path, text}`), captured by both adapters for
  `LICENSE*`/`COPYING*` files, path-sorted; the first id that identifies wins; no
  file or no identification → silent (never guessed). The key is present only
  when a LICENSE file is captured, so every Part A-D bench snapshot is
  byte-identical to E1.
- New unit tests: identification order (LGPL before GPL), `cc-by` vs `cc-by-nc`
  via `forbidden`, copyright + wrapped-line normalization, unidentifiable →
  silent, declared-vs-file mismatch → `license_inconsistent`, all nine ids
  identify.

## 2. Step 2 — `contamination-v1` 1.1.0 real suites as n-gram hashes

- Bumped **1.0.0 → 1.1.0**. Synthetic `benchsuite-alpha`/`beta` untouched (still
  plain `items`, no `kind`), so their byte-identical regeneration is preserved.
- Real suites added as `kind:"ngram-hashes"` — storing **only the sha256 hashes
  of normalized word 13-grams** (W5 normalization, D-32), never raw benchmark
  text (D-38):
  - `gsm8k-test` — `openai/gsm8k` @ `740312ad…`, config `main`, split `test`,
    field `question`: 1319 items → **45,164** 13-gram hashes.
  - `squad-validation` — `rajpurkar/squad` @ `7b6d24c4…`, config `plain_text`,
    split `validation`, field `context`: 523 unique contexts (first 3000 rows) →
    **46,276** hashes.
- Sources fetched once (`python -m releaseseal.rules.build_packs fetch`, HF
  datasets-server) into `fixtures/contamination/*.json` (pinned source snapshots,
  checked in). `build_contamination_pack()` and the tests read only those, so the
  pack regenerates **byte-identically offline**. W5 gained a hashed-suite leg via
  the shared `ngram_hash_set` helper. A suite that cannot be fetched is reported
  not-run, never fabricated (both fetched here).

## 3. Step 3 — Part B-D real-dataset audit

### 3.1 Frozen selection (`bench/partbd/datasets.json`, `partbd-datasets/1`)

Rule-pinned then frozen (committed `314b2b1`, **before** the audit): HF datasets
sorted by downloads desc; public & not gated & not disabled & ≥1 inventoriable
data file; strata filled — non-English/multilingual **7** (≥6), Croissant **35**
(≥4), >1M rows **10** (≥4), license families **permissive 20 / copyleft 3 /
non_commercial 1 / other_or_unknown 12**. Revisions pinned to the HEAD sha at
freeze (`frozen_at` 2026-11-11T06:35:56Z). Gated datasets excluded, never
authenticated against.

| dataset | revision | declared license | family | non-EN | Croissant | sampled/total rows |
|---|---|---|---|:--:|:--:|---|
| `Salesforce/wikitext` | b08601e04326 | cc-by-sa-3.0 | copyleft | 1 | 1 | 400/1809468 |
| `openai/gsm8k` | 740312add88f | mit | permissive | 1 | 1 | 400/8792 |
| `nyu-mll/glue` | bcdcba79d07b | other | other | 1 | 1 | 400/795241 |
| `allenai/ai2_arc` | 210d026faf99 | cc-by-sa-4.0 | copyleft | 1 | 1 | 400/5197 |
| `cais/mmlu` | c30699e8356d | mit | permissive | 1 | 1 | 400/115700 |
| `uoft-cs/cifar10` | 0b2714987fa4 | unknown | other | 1 | 1 | 400/60000 |
| `hallucinations-leaderboard/results` | 30f759225f89 | apache-2.0 | permissive | 0 | 1 | 0/None |
| `nicoboou/IDRCell100k` | ba8b95954a27 | — | other | 0 | 1 | 0/308899 |
| `m-a-p/FineFineWeb` | 7fd92dc825a7 | apache-2.0 | permissive | 0 | 1 | 0/1646140 |
| `epfml/FineWeb-HQ` | e58199cdd524 | odc-by | permissive | 0 | 1 | 200/2445786576 |
| `mvp-lab/LLaVA-OneVision-1.5-Mid-Training-85M` | 6ca51e61173b | apache-2.0 | permissive | 0 | 1 | 0/91493097 |
| `Lichess/standard-chess-games` | de4e636eddf5 | cc0-1.0 | permissive | 0 | 1 | 200/7136017970 |
| `HuggingFaceFW/fineweb-edu` | 87f09149ef47 | odc-by | permissive | 0 | 1 | 200/1525223056 |
| `applied-ai-018/pretraining_v1-omega_books` | 54b95f40c52b | — | other | 0 | 1 | 200/103802366 |
| `xlangai/ubuntu_osworld_file_cache` | 1e112283c4ec | apache-2.0 | permissive | 0 | 1 | 0/None |
| `wikimedia/wikipedia` | b04c8d1ceb2f | cc-by-sa-3.0 | copyleft | 1 | 1 | 200/6407814 |
| `OPR-Project/OxfordRobotCar_OpenPlaceRecognition` | 14ac6ad1df25 | cc-by-nc-sa-4.0 | non_commercial | 0 | 1 | 0/None |
| `ayuo/hd_tmp` | 9d6e041a87e3 | — | other | 0 | 0 | 0/None |
| `roisincrtai/ptb-xl-1.0.3` | 8caff550132c | — | other | 0 | 1 | 200/87858 |
| `ryanmarten/OpenThoughts-1k-sample` | a82400884621 | — | other | 0 | 1 | 200/1000 |
| `mlfoundations/MINT-1T-HTML` | 906a8b85cea6 | cc-by-4.0 | permissive | 0 | 1 | 200/897871 |
| `lerobot/FineART` | 15746b76ddc2 | cc-by-4.0 | permissive | 0 | 1 | 0/None |
| `pulmo/ncbi-genbank-complete` | 7f2fd793a45f | apache-2.0 | permissive | 0 | 1 | 0/None |
| `open-cn-llm-leaderboard/requests` | 3bb01c2e65ee | apache-2.0 | permissive | 0 | 1 | 0/None |
| `world-igr-plum/regions` | f15723da1af8 | mit | permissive | 0 | 1 | 0/None |
| `huggingface/DEH-image-scan-data` | efac82456c5a | — | other | 0 | 1 | 6/6 |
| `open-index/hacker-news` | c54ced5973b9 | odc-by | permissive | 0 | 1 | 0/None |
| `ThomasTheMaker/ptb-xl-ecg` | ef558e84986f | — | other | 0 | 1 | 200/87858 |
| `visionhdstream/data-vision-01` | a7055cc76c65 | — | other | 0 | 1 | 200/222 |
| `TIGER-Lab/MMLU-Pro` | b189ec765aa7 | mit | permissive | 0 | 1 | 270/12102 |
| `Salesforce/GiftEvalPretrain` | 6830b624de7e | apache-2.0 | permissive | 0 | 1 | 0/None |
| `hallucinations-leaderboard/requests` | 237c75394f04 | apache-2.0 | permissive | 0 | 1 | 0/None |
| `anon8231489123/ShareGPT_Vicuna_unfiltered` | 192ab2185289 | apache-2.0 | permissive | 0 | 1 | 0/None |
| `HuggingFaceFW/fineweb` | 9bb295ddab0e | odc-by | permissive | 0 | 1 | 200/518458467 |
| `ahnaftaz/locus-commit-pool-v1` | 6883f90b50d8 | other | other | 0 | 1 | 0/None |
| `carlotabronze/sm-stuff` | 009a2baf2184 | — | other | 0 | 1 | 0/None |

### 3.2 Run

`bench/partbd/run_partbd.py` + the live `DatasetHttpFetcher` (datasets-server
rows, `dsample/1` cap `rows_per_split=200`, `max_splits=2`, D-40; largest
row-served config, D-41; polite rate-limiting + 429/5xx backoff). **36/36 ok, 0
errors.** Metadata + capped samples only; $0 spend; no bulk downloads. Outputs:
`audit/partbd/{dataset}.snap.json` (sample row text **omitted** — raw third-party
content / possible PII never persisted, D-40), `audit/partbd/{dataset}.pack.json`
(`pack/2`, W4 values **masked**, D-31), and `audit/partbd/summary.json`
(`partbd-summary/1`). Rule packs used: `dataset-hub-v1` 1.1.0, `contamination-v1`
1.1.0, `lid-v1` 1.0.0, `license-terms-v1` 1.0.0.

### 3.3 Results (captured 2026-11-11)

Counted = `heuristic == false` AND `severity != "info"` (D-31). **13/36** datasets
yielded ≥1 counted finding. Counted-finding rate by class: W1 **0.278**, W2/W3/W5/W6
**0.000**, W4 **0.028 datasets** (but 40 hits over 7 datasets — see below),
W7 **0.028 datasets**.

Code totals (all severities): `declared_language_absent` 321, `card_field_missing`
209, `pii_detected` 40, `dedup_measured` 19, `license_unknown` 10,
`contamination_measured` 1.

Strata (prompt's reality rule):
- **Claim violations** (a real declaration is violated): **321** — *all* from
  `wikimedia/wikipedia`'s W7 `declared_language_absent`. Its card declares ~320
  languages, but the sample came from a single language config, so every other
  declared language measured 0. This is a **sampling-coverage artifact, not a
  real falsification** (the dataset genuinely contains those languages in other
  configs); it is the one meaningful W7 limitation this audit surfaced. **No
  other dataset produced any claim-violation** — consistent with the design's
  core finding that real dataset cards use almost none of our structured
  declaration vocabulary.
- **Measurements** (info + detector hits): 269. W4 detector hits 40 across 7
  web-crawl corpora (`email` 29, `card_luhn` 9, `ipv4` 2; all masked);
  `card_luhn` on web text is Luhn-valid-by-chance noise — high-precision format,
  not confirmed card numbers. W5 measured overlap > 0 on 1 dataset
  (`openai/gsm8k` vs `gsm8k-test` 0.502 — the suite's own source; circular but a
  correct measurement). W6 `dedup_measured` on all 19 text-sampled datasets.
- **W1 `license_unknown`** (low, counted): 10 datasets whose declared license is
  not in `license-terms-v1`'s 12-entry table (`cc-by-sa-3.0`, `odc-by`,
  `cc0-1.0`, `other`, `unknown`) → "undeterminable", never an inferred verdict.
- **W1 `license_inconsistent`**: **0** — Croissant license normalization (D-39)
  removed format-only artifacts, and no identified LICENSE file disagreed with
  the declared id.
- **W8 completeness gaps** (signal only): **100%** — every real card is missing
  at least one declaration field.

### 3.4 Predictions scored (hit/miss)

| id | prediction | threshold | measured | verdict |
|---|---|:--:|:--:|:--:|
| P1 | ≥60% datasets ≥1 counted finding | 0.60 | **0.361** (13/36) | MISS |
| P2 | W1 license inconsistency in ≥25% | 0.25 | **0.000** | MISS |
| P3 | W4 detector hits in ≥15% | 0.15 | **0.194** (7/36) | **HIT** |
| P4 | W5 measured overlap >0 in ≥10% | 0.10 | **0.028** (1/36) | MISS |
| P5 | W7 declared-language problems in ≥10% | 0.10 | **0.028** (1/36) | MISS |
| P6 | W8 completeness gaps in ≥50% (signal) | 0.50 | **1.000** | **HIT** |

**2 hits, 4 misses.** The predictions were optimistic in the same direction the
model-side GATE 2 history warns about. Honest reading: (a) the W8 100% result and
the near-total absence of claim violations confirm the design's thesis — dataset
cards carry almost none of the machine-readable claims the W-checks grade, so the
module's value on real data is **measurement at stated coverage**, not claim
falsification; (b) content coverage is thin because top-download corpora are
largely binary/parquet or not row-served by datasets-server (17/36 empty sample);
(c) W4 detector hits (P3) do occur materially on web-crawl text, as predicted.

### 3.5 Coverage caveats

- **19/36 datasets** got a content sample; **17/36** have an empty sample
  (`cov=0`) — image/audio/binary corpora, single-file datasets, or configs
  datasets-server does not row-serve. Recorded per dataset; one dataset never
  aborts the run.
- Content sample is a **prefix window** (`rows_per_split=200`, first `max_splits=2`
  splits of the largest row-served config), not a full-corpus reservoir — the
  `dsample/1` rule id is kept with the actual parameters recorded (D-40). True
  split totals are the coverage denominator.
- The pack **never certifies absence** of PII/contamination/dedup; all content
  findings are measurements at the stated coverage.
- `wikimedia/wikipedia` W7 artifact (§3.3) is the clearest coverage limitation:
  multilingual cards sampled from one language config over-fire
  `declared_language_absent`.

## 4. Regression + tests (re-run this session)

- **Full suite: 141 passed**, offline, no network (E1's 129 + 12 new E2 tests).
- **Part A-D dev bench unchanged:** `cases_sha256`
  `0e2633a26ed15c72b585e00697c4b1f013d212a0630e214f0c9a33bc21a4ab32`
  (byte-identical to E1), per-class recall **W1–W7 all 1.000**, clean FP
  **0.000** → **GATE E1 still PASS**. The real contamination suites did not create
  any spurious overlap on the synthetic clean cases.
- **Model side intact:** model GATE 1 recall V1–V7 all 1.000, clean FP 0.000;
  `contamination-v1`/`lid-v1` regenerate byte-identically; `license-terms-v1`
  byte-unchanged; model `pack/1` path untouched (D-35).

## 5. Deviations (each with a DECISIONS id)

- **D-37** — W1 LICENSE-file identification data lives in `dataset-hub-v1` 1.1.0
  (not `license-terms-v1`, kept byte-unchanged), switching on the leg D-29 parked.
- **D-38** — `contamination-v1` 1.1.0 real suites stored as 13-gram **hashes
  only**, never raw benchmark text; SQuAD uses `context` (questions are mostly
  <13 words) and contexts are deduped.
- **D-39** — Croissant license normalized to an SPDX id so W1 does not
  manufacture format-only inconsistencies on HF auto-Croissant.
- **D-40** — Part B-D operational pins: frozen selection, `dsample/1` prefix-window
  sampling cap (parameters recorded), on-disk snapshot redaction of raw sample
  text.
- **D-41** — Part B-D fetcher picks the largest **row-served** config, with polite
  rate-limiting + retry; corrected twice for coverage **before any result was
  committed**, never toward the frozen predictions.

## 6. Status for the gate session

**GATE E2 is not judged here.** This session delivered the build + the Part B-D
audit with full disclosure (every dataset, no cherry-picking; predictions scored
hit/miss; coverage caveats stated). The sealed holdout is authored and scored by
separate sessions; that scoring session issues the GATE E2 verdict against the
holdout bars (recall ≥ 0.85 per W1–W7, clean FP ≤ 5%). Module B (AIBOM) is a
separate session. **Fabrication of results is prohibited** — every number here is
from committed code this session (`pytest`, `bench-d score`, `run_partbd.py`);
nothing was hand-set, and nothing not run is reported as run.
