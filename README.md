# ReleaseSeal

**An offline, deterministic verifier for model-release documentation.** Given a
model release — a Hugging Face repo at a pinned revision, or a local directory —
ReleaseSeal checks whether the release's **documentation and declared metadata
agree with its artifacts and with each other** (config facts, file hashes,
license lineage), and emits a schema-versioned, **hash-chained evidence pack**
plus a human-readable report that anyone can re-verify offline.

> ReleaseSeal produces **evidence**, not a certificate. It reports consistency and
> completeness of a release's documentation; it does **not** certify legal
> compliance, "passing", or fitness for any purpose. A finding is a pointer to a
> place to check, not a verdict.

No servers, no paid APIs, no weight downloads (metadata + small files only), and
deterministic: the core is a pure function `snapshot JSON → findings JSON`.

**Links:** interactive demo (Static Space) —
<https://huggingface.co/spaces/NagaYu/releaseseal-demo> · bench dataset —
<https://huggingface.co/datasets/NagaYu/releaseseal-bench>

## 1. What it is

Eight verification classes over a versioned release **snapshot**:

- **V1 artifact–record mismatch** — files referenced but absent, undocumented
  weights, hash disagreements, safetensors-index size inconsistencies.
- **V2 architecture & scale** — card claims (parameters, context length,
  architecture, base-model relation) vs `config.json` facts and a derived
  parameter estimate.
- **V3 license lineage** — walks the `base_model` chain (recursively, depth-capped,
  cycle-guarded) and checks the declared license against every ancestor, plus
  attribution/NOTICE propagation; unknown ancestors are "undeterminable", never
  guessed compatible.
- **V4 mandatory documentation presence** — EU AI Act Annex XI / XII + GPAI Code
  of Practice items (a **screening signal** — see §6).
- **V5 staleness / revision drift** — card/model-index pointing at another
  revision, stale `as-of` dates, eval results naming another checkpoint.
- **V6 evaluation-claim inconsistency** — model-index vs result files, internal
  conflicts, prose claims contradicting structured values (scale-aware).
- **V7 release completeness** — tokenizer/chat-template/generation-config/weight-map
  internal consistency (can it be loaded as documented?).
- **V8 undeclared-derivation signal** — a heuristic config-fingerprint signal,
  **never** a gate input.

Regulatory and license logic lives in **versioned rule packs** (data), so a legal
amendment is a data release, not a code change.

## 2. Headline result — Part B (audit of 40 popular public models)

A pinned-revision audit of 40 widely-downloaded Hugging Face models, verified with
the frozen verifier (`gpai-eu-v3`), metadata-only. Authoritative figures are from
`reports/partb-v3.md`. Reported **per item**, as missing-documentation counts
(not a bare overall rate):

| Documentation item (EU AI Act) | models missing it |
|---|---|
| Copyright policy — Art. 53(1)(c) | **40 / 40** |
| Public training-content summary — Art. 53(1)(d) | **38 / 40** |
| Training compute — Annex XI 2(d) | **34 / 40** |
| Energy consumption — Annex XI 2(e) | **33 / 40** |
| Testing/validation process — Annex XI 1(e) | **30 / 40** |
| Distribution channels — CoP form | **26 / 40** |
| Acceptable-use policy — Annex XII 2 | **21 / 40** |
| Downstream-integration info — Annex XII 1 | **19 / 40** |
| Evaluation results — Annex XI 2(g) | 14 / 40 |
| Intended use — Annex XI 1(a) | 13 / 40 |
| Input/output modality — Annex XII 3 | 7 / 40 |
| Training-data summary — Annex XI 2(c) | 6 / 40 |

Every audited card is missing at least one item; the most pervasive real gaps are
a **copyright policy** and a **public training-content summary**. **Disclosure:**
2 of the 40 models (`google/gemma-2-2b`, `meta-llama/Llama-3.2-1B`) are gated, so
their `config.json` could not be fetched — their inspection surface was narrower
(card metadata only), not a clean bill. Full per-model detail, with evidence
pointers and v1→v2→v3 comparison, is in `reports/partb.md`, `partb-v2.md`,
`partb-v3.md`.

## 3. How to run

```bash
python3 -m pytest -q                         # offline test suite
export PYTHONPATH=src

# build a snapshot (local directory, or a recorded HF API bundle — no network)
python3 -m releaseseal snapshot --local ./some-release -o snap.json
python3 -m releaseseal snapshot --hf org/model --hf-fixture fixtures/hf/real-tiny-gpt2.json -o snap.json

python3 -m releaseseal verify snap.json -o findings.json
python3 -m releaseseal pack   snap.json -o pack.json --report report.md
python3 -m releaseseal verify-pack pack.json --snapshot snap.json   # offline re-verify

# synthetic bench
python3 -m releaseseal bench generate --seed 0 --ext -o out/bench
python3 -m releaseseal bench score --manifest out/bench/manifest.json
```

A live metadata fetch (for the Part B audit) uses only the HF API and small files;
weights are never downloaded.

## 4. Bench results

- **dev split** (120 synthetic cases): per-class recall **1.000** (V1–V7), clean
  false-positive rate **0.000**.
- **dev_ext** (multi-level lineage): V3 recall **1.000**, lineage-walk accuracy
  **1.000**.
- **Sealed holdouts** (three independently-authored sets, each scored once with
  the frozen verifier): recall rose across the rounds as the verifier was aligned,
  reaching **per-class recall V1–V7 = 1.000 on the final set (v3)**. Earlier sets
  (scored against earlier verifier states): v1 — V5 0.750, V6 0.500, V7 0.875
  (V1–V4 1.000); v2 — V6 0.750 (V1–V5, V7 1.000). The cross-artifact checks and the
  recursive-lineage machinery generalise cleanly to independent data. (Holdout
  cases are never published; only aggregates.)

## 5. Gate history (honest)

| gate | set | result | why |
|---|---|---|---|
| GATE 1 | dev synthetic (120) | **PASS** | recall ≥0.90 all V1–V7, clean FP ≤5% |
| GATE 2 | holdout v1 (sealed) | **FAIL** | V4 fixed-phrase matching too brittle → 100% clean FP |
| re-gate | holdout v2 (sealed) | **FAIL** | V4 item-set mismatch + phrasing misses → 100% clean FP |
| final re-gate | holdout v3 (sealed) | **FAIL** | V4 phrasing only (item-set fixed): clean FP **82%**; **recall V1–V7 all 1.000** |

Under a pre-recorded stop rule, after three GATE 2 FAILs there is **no further fix
round and no fourth holdout** — the result is **published as-is**. Every FAIL was
on V4 clean false positives; recall was strong throughout and perfect on the final
set. See `reports/phase2.md`, `phase2-fix.md`, `phase2-align.md`.

## 6. Known limitation — V4 is a screening signal

V4 (documentation presence) is a **pattern-based screening signal**, not a decided
gap. On the large real-card audit it catches genuine missing items at high recall
(§2), but on **fully-documented** cards written in independent natural wording it
still **over-fires**: on the final sealed holdout, clean false-positive rate was
**82%**, decomposed as `xi.energy` 13, `xii.downstream_integration` 8,
`xi.testing_process` 7, `xi.training_process` 7, `xi.compute` 5 (of 28 clean
cards). A finite pattern set cannot anticipate the open space of natural phrasing
(e.g. energy stated as "… MWh of electricity … tCO2e").

**Read a V4 finding as "a place to check", not "a confirmed omission."** By
contrast, **V1–V3 and V5–V7 are artifact checks** (hashes, config facts, license
lineage, loadability) with a different, far lower false-positive character — their
findings point at concrete, verifiable inconsistencies.

## 7. Rule packs & the EU AI Act

Regulatory content is versioned data:

- `hub-metadata-v1` — Hub card-field conventions.
- `gpai-eu-v1` → `v2` → `v3` — EU AI Act **Annex XI / Annex XII** + GPAI Code of
  Practice items, each citing its article/annex; v3 uses content-word matching.
  The 16-item set is single-sourced (`docs/authoring-item-set.md`).
- `license-terms-v1` — a license-compatibility data model (not legal advice).
- `fingerprints-v1` — V8 signal data.

Why now: EU AI Act Chapter V (GPAI) duties apply since 2025-08-02; **enforcement
began 2026-08-02** (fines up to 3% of turnover or €15M); models placed on the
market before 2025-08-02 must comply by **2027-08-02**. Findings always cite the
rule-pack version, so legal drift degrades gracefully.

## 8. License / contact

**All Rights Reserved**, transfer / license-available — see `LICENSE`. The only
contact route is the portfolio: <https://nagayu-portfolio.nagayu.workers.dev/en>.
Sealed holdout content is never published; this repository ships the code, the
synthetic dev/dev_ext bench, the rule packs, the real-model audit reports, and the
full gate history.

## 9. Dataset releases (Module D)

The same claims-vs-artifacts engine, widened to **dataset releases** (a Hugging
Face dataset repo at a pinned revision, or a local dataset directory). W1–W7 are
deterministic checks; W8 is a signal. **Every W-check binds only to structured
declarations** (card YAML fields, Croissant metadata, LICENSE files, structured
tags) — never to prose, which is where the model side's V4 over-fired. Where a
claim exists only in prose, the module measures the underlying fact and reports it
as an audit fact, never as a claim violation.

- **W1 license consistency** — declared license vs Croissant vs LICENSE file vs the
  versioned license-terms table; an out-of-table license is reported
  *undeterminable*, never guessed.
- **W2 source-license rollup** · **W3 inventory truth** (files/splits/row counts) ·
  **W4 PII** (high-precision detectors; values masked; falsification/measurement
  only, never certifies absence) · **W5 benchmark contamination** (pinned n-gram
  overlap vs versioned suites) · **W6 dedup** (MinHash at pinned parameters) ·
  **W7 composition drift** (pinned language-ID over the sample vs declared shares).
- **W8 dataset-card completeness** — a heuristic signal only, excluded from gates
  and headlines (the V4 lesson).

Content checks run on a **pinned deterministic sample** (`dsample/1`), and every
content finding cites its coverage — the pack never implies full-corpus
certification.

### Gate results (dataset side)

| gate | set | result | bars |
|---|---|---|---|
| GATE E1 | dev synthetic (120, seed 20261111) | **PASS** | recall ≥0.90 all W1–W7, clean FP ≤5% |
| GATE E2 | sealed holdout (120, seed 20261112) | **PASS** | recall ≥0.85 all W1–W7, clean FP ≤5% |

GATE E2 measured per-class recall **1.000** for all of W1–W7 and clean FP **0.000**,
beating every preregistered prediction (0.85–0.97). **Read with its caveat:** the
holdout is *synthetic and co-designed* with the same W-check vocabulary that scores
it — a perfect synthetic recall is **not** a real-world recall estimate. The honest
real-data statement is the Part B-D audit below. (Holdout cases are never published;
only aggregates. See `reports/phase-e1.md`, `phase-e2.md`.)

### Headline — Part B-D real dataset audit (36 datasets)

A live, pinned-revision audit of **36** popular public HF datasets (metadata +
`dsample/1`-capped sample; **36/36 ran, 0 errors, $0**; no weight downloads). Full
results, per-dataset and with no cherry-picking, are in `hf-audit/partbd-results.md`
and `hf-dataset/partbd-summary.json`.

The real-data result is a **measurement** result, not a falsification result:
real dataset cards carry almost none of the machine-readable declarations the
W-checks grade, so there is almost nothing to violate.

- **W8 completeness gaps: 100%** — every one of the 36 cards is missing ≥1
  declaration field (the headline figure; W8 is signal-only).
- **Claim violations ≈ 0.** `license_inconsistent` 0/36; `license_unknown`
  (undeterminable) 10/36; the only `declared_language_absent` findings (321) are all
  from one dataset (`wikimedia/wikipedia`) and trace to **single-config sampling** —
  a coverage limitation of the audit, **not** a falsification, and not counted as a
  violation.
- **W4 PII detectors** — format hits only, all values masked (email 29, card_luhn 9,
  ipv4 2) across 7 web-crawl corpora; the 9 `card_luhn` hits are
  Luhn-valid-by-chance strings, **not** confirmed card numbers.
- **Coverage:** 19/36 datasets yielded a content sample; 17/36 are binary / not
  row-served. **13/36** had ≥1 counted finding.
- **Preregistered predictions: 2 HIT / 4 MISS** (disclosed) — optimistic in the same
  direction the model-side GATE 2 history warned about.

### How to run (dataset side)

```bash
export PYTHONPATH=src
# build a dataset snapshot (local dir, or a recorded HF dataset bundle — no network)
python3 -m releaseseal dsnapshot --local ./some-dataset -o dsnap.json
python3 -m releaseseal dsnapshot --hf-dataset org/name \
  --hf-dataset-fixture fixtures/hf/dataset-tiny-clean.json -o dsnap.json
python3 -m releaseseal verify dsnap.json -o findings.json      # dispatches on schema
python3 -m releaseseal pack   dsnap.json -o pack.json --report report.md

# synthetic dataset bench (Part A-D)
python3 -m releaseseal bench-d generate --seed 20261111 -o out/bench_d
python3 -m releaseseal bench-d score --manifest out/bench_d/manifest.json
```

## 10. AIBOM import/export (Module B)

CycloneDX ML-BOM and SPDX 3.0 AI documents are first-class inputs and outputs, so a
BOM arriving inside an enterprise release bundle can be graded by the same engine.

- **Import:** CycloneDX **1.5 / 1.6 / 1.7** and **SPDX 3.0 AI** (JSON-LD) →
  components, licenses, hashes, dependency edges (hashes normalized across formats).
- **Four decidable checks** (`check="B1"`), each tested positive and negative:
  `bom_hash_mismatch` (high), `bom_license_mismatch` (medium), `bom_dangling_ref`
  (medium, pure document), `bom_undeclared_artifact` (medium).
- **`unverifiable` is a first-class, counted outcome** — a BOM whose described
  artifacts are not in hand is *measured as unverifiable* (with a reason), never
  silently passed and never a finding. No semantic judgement is ever made.
- **Export:** emit a CycloneDX 1.6 ML-BOM from any evidence pack (model or dataset);
  export → import round-trips the component set; output is byte-deterministic.
- **Mini-bench:** 24 planted-defect cases, exact-match **24/24** — a regression
  check, **not** a gate (no holdout; the decidable class set is small and fully
  decidable).

```bash
export PYTHONPATH=src
python3 -m releaseseal bom import fixtures/bom/cyclonedx-1.6-model.json \
  --artifacts fixtures/bom/artifacts-model-clean.snap.json -o bom-result.json
python3 -m releaseseal bom export pack.json --snapshot snap.json -o mlbom.json
```

Full test suite (model + dataset + BOM): **183 passed**, offline. See
`reports/phase-e2-bom.md`.
