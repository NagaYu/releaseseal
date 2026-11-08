---
license: other
license_name: all-rights-reserved
pretty_name: ReleaseSeal Bench (dev + dev_ext)
task_categories:
  - other
tags:
  - model-cards
  - documentation-verification
  - eu-ai-act
  - synthetic
size_categories:
  - n<1K
---

# ReleaseSeal Bench — dev + dev_ext

Synthetic benchmark for **ReleaseSeal**, an offline verifier of model-release
documentation/artifact consistency. These are the **public development splits**;
the sealed holdout sets used for gating are **not** published (only aggregate
scores are, in the project's reports).

> This dataset supports evidence-based *screening* of model-release documentation.
> ReleaseSeal is not a certification and does not attest compliance.

## Contents

| file | cases | what it is |
|---|---|---|
| `dev-manifest.json` | 120 | V1–V7 planted (12 each) + 36 clean, incl. near-miss cleans |
| `dev_ext-manifest.json` | 24 | multi-level license-lineage cases (grandparent violations, unknown intermediates, deep clean) |

Each case is `{id, kind, expected, snapshot}`, where `snapshot` is a full
`snapshot/1` object (metadata only — **no weight bytes**). `kind` is a class id
`V1`–`V7` or `clean`; `expected` lists the planted class (empty for clean).
`dev_ext` cases add `lineage_truth` (the planted violating-ancestor set) for a
lineage-walk-accuracy metric.

## Schema (snapshot/1, summary)

Top level: `schema_version`, `captured_at`, `source` (`adapter`, `repo_id`,
`revision`, `path`), `files[]` (`path`, `size`, `sha256`, `hash_source`), `card`
(`yaml`, `prose`, `claims`), `config`, `generation_config`, `tokenizer_config`,
`chat_template`, `safetensors_index`, `model_index`, `result_files`,
`snapshot_sha256`, and an optional flat `lineage` map for ancestors. Full spec in
the project `SPEC.md`.

## How it was generated

Deterministically, stdlib only, no network. From the project repository:

```bash
PYTHONPATH=src python3 -m releaseseal bench generate --seed 0 --ext -o out/bench
```

`dev` is `seed=0` (`cases_sha256` begins `5267e1a0…`); `dev_ext` is a separate
seeded stream (`cases_sha256` begins `eb636f26…`). Re-running reproduces
byte-identical manifests.

## Results on these splits

- dev: per-class recall **1.000** (V1–V7), clean false-positive rate **0.000**.
- dev_ext: V3 recall **1.000**, lineage-walk accuracy **1.000**.

## Holdout policy

Three independently-authored **sealed** holdout sets were used for GATE 2 scoring.
Their cases are **never** published; only aggregate scores appear in the reports.
Per-class recall V1–V7 was **1.000 on the final set (v3)**; earlier sets scored
lower on some classes (v1 — V5 0.750, V6 0.500, V7 0.875; v2 — V6 0.750). Every
gate failed on V4 clean false positives (documentation-presence screening is
pattern-based — see the project README §6). This is disclosed, not hidden.

## License / contact

All Rights Reserved, transfer/license-available. Contact:
<https://nagayu-portfolio.nagayu.workers.dev/en>.
