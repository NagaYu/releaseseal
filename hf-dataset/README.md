---
license: other
license_name: all-rights-reserved
pretty_name: ReleaseSeal Bench (models + datasets)
task_categories:
  - other
tags:
  - model-cards
  - dataset-cards
  - documentation-verification
  - aibom
  - eu-ai-act
  - synthetic
size_categories:
  - n<1K
---

# ReleaseSeal Bench — models + datasets

Synthetic benchmark + real-audit summaries for **ReleaseSeal**, an offline,
deterministic verifier of **release documentation vs artifacts** — now covering
**model releases** (V1–V8) and **dataset releases** (W1–W8, Module D), plus an
**AIBOM** import/export module (Module B). These are the **public development
splits** and **aggregate audit summaries**; the sealed holdout sets used for gating
are **not** published (only aggregate scores are, in the project's reports).

> This dataset supports evidence-based *screening* of release documentation.
> ReleaseSeal is not a certification and does not attest compliance. A finding is a
> place to check, not a verdict.

**Links:** interactive demo (Static Space) —
<https://huggingface.co/spaces/NagaYu/releaseseal-demo> · code —
<https://github.com/NagaYu/releaseseal>

## Contents

| file | cases | what it is |
|---|---|---|
| `dev-manifest.json` | 120 | **model** dev: V1–V7 planted (12 each) + 36 clean, incl. near-miss cleans |
| `dev_ext-manifest.json` | 24 | **model** multi-level license-lineage cases |
| `dev-d-manifest.json` | 120 | **dataset** dev (Module D): W1–W7 planted (12 each) + 36 clean |
| `partbd-summary.json` | 36 | **dataset** real-audit summary (`partbd-summary/1`): per-dataset + aggregate |

Each bench case is `{id, kind, expected, snapshot}`. For the model splits `snapshot`
is a `snapshot/1` object and `kind` ∈ `V1`–`V7`/`clean`; for the dataset split
`snapshot` is a `dsnapshot/1` object and `kind` ∈ `W1`–`W7`/`clean`. `expected`
lists the planted class (empty for clean). All snapshots are metadata only —
**no weight bytes**. `dev_ext` cases add `lineage_truth`.

## Model bench (V1–V8)

Top level of `snapshot/1`: `schema_version`, `captured_at`, `source`, `files[]`,
`card`, `config`, `generation_config`, `tokenizer_config`, `chat_template`,
`safetensors_index`, `model_index`, `result_files`, `snapshot_sha256`, optional flat
`lineage`. Generate deterministically (stdlib only, no network):

```bash
PYTHONPATH=src python3 -m releaseseal bench generate --seed 0 --ext -o out/bench
```

`dev` is `seed=0` (`cases_sha256` begins `5267e1a0…`); `dev_ext` is a separate
seeded stream (`cases_sha256` begins `eb636f26…`). Results: dev per-class recall
**1.000** (V1–V7), clean FP **0.000**; dev_ext V3 recall **1.000**, lineage-walk
accuracy **1.000**.

## Dataset bench (W1–W8, Module D)

`dsnapshot/1` carries the dataset inventory (files, splits, row counts), card YAML +
Croissant declarations, LICENSE files, and a pinned content sample (`dsample/1`).
W1–W7 are deterministic checks that bind **only to structured declarations**; W8 is
a card-completeness signal (never a gate). Generate deterministically:

```bash
PYTHONPATH=src python3 -m releaseseal bench-d generate --seed 20261111 -o out/bench_d
PYTHONPATH=src python3 -m releaseseal bench-d score --manifest out/bench_d/manifest.json
```

`dev-d` is `seed=20261111`, `cases_sha256` begins `0e2633a2…`, 120 cases (W1–W7 × 12
+ 36 clean), re-generating byte-identically. **GATE E1 = PASS** and **GATE E2 = PASS**
(sealed holdout, seed 20261112): per-class recall **1.000** W1–W7, clean FP **0.000**.
**Caveat:** the dev/holdout splits are *synthetic and co-designed* with the W-check
vocabulary, so a perfect synthetic recall is **not** a real-world recall estimate —
the real-data statement is Part B-D below.

## Part B-D — real dataset audit (36 datasets, `partbd-summary.json`)

A live, pinned-revision audit of 36 popular public HF datasets (metadata +
`dsample/1`-capped sample; 36/36 ran, 0 errors, $0; no weight downloads). The result
is a **measurement** result, not a falsification result — real dataset cards carry
almost none of the machine-readable declarations the W-checks grade:

- **W8 completeness gaps: 100%** — every one of the 36 cards is missing ≥1
  declaration field (headline; signal-only).
- **Claim violations ≈ 0.** `license_inconsistent` 0/36; `license_unknown`
  (undeterminable) 10/36. The only `declared_language_absent` findings (321) are all
  from one dataset (`wikimedia/wikipedia`) and trace to single-config sampling — a
  **coverage limitation of the audit**, not a falsification, and not counted as a
  violation.
- **W4 PII detectors** — format hits only, all values masked (email 29, card_luhn 9,
  ipv4 2) across 7 web-crawl corpora; the 9 `card_luhn` hits are
  Luhn-valid-by-chance strings, **not** confirmed card numbers.
- **Coverage** 19/36 content-sampled, 17/36 binary / not row-served; **13/36** had
  ≥1 counted finding. **Preregistered predictions: 2 HIT / 4 MISS** (disclosed).

Per-dataset detail (all 36, no cherry-picking) is in the repository at
`hf-audit/partbd-results.md`; the machine-readable summary is `partbd-summary.json`
here.

## AIBOM (Module B)

CycloneDX 1.5/1.6/1.7 + SPDX 3.0 AI import → graded by the same engine; four
decidable checks (hash/license mismatch, dangling ref, undeclared artifact);
`unverifiable` is a first-class counted outcome, never a silent pass. Export → a
CycloneDX 1.6 ML-BOM from any evidence pack. Mini-bench 24/24 exact (regression,
not a gate).

## Holdout policy

Sealed, independently-authored holdout sets are used for gate scoring and are
**never** published — only aggregate scores appear in the reports. On the model
side, three sealed sets were scored (GATE 2 FAIL ×3, on V4 clean false positives —
disclosed, not hidden; recall V1–V7 1.000 on the final set). On the dataset side, a
sealed holdout exists and is never published (GATE E2 = PASS). No holdout hashes or
case composition are published here.

## License / contact

All Rights Reserved, transfer/license-available. Contact:
<https://nagayu-portfolio.nagayu.workers.dev/en>.
