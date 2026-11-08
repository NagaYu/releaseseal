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
