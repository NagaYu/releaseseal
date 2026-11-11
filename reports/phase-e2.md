# Phase E2 — GATE E2 scoring report

Final E2 session. The build half (`reports/phase-e2-build.md`), Module B
(`reports/phase-e2-bom.md`), and the sealed holdout (`bench/holdout_d/manifest.json`)
were delivered by their own prior sessions. **This session scores the sealed
holdout exactly once** with the current frozen verifier and issues the GATE E2
verdict. No verifier code was changed before, during, or after scoring.

House standard (v1 precedent: GATE 2 FAIL ×3, published disclosed): the result is
reported exactly as measured. A FAIL is a publishable result; a fudged PASS is not.

---

## 0. Preconditions (verified before scoring)

| precondition | result |
|---|---|
| `reports/phase-e2-predictions.md` exists, committed **before** E2 build code | ✓ — commit `f3b9cba` (Phase E2 Step 0), unchanged since; build code commits `f077f8e` (Part B-D) and `90292a4` (Module B) are later |
| holdout manifest at `bench/holdout_d/manifest.json` | ✓ — `schema_version: bench-manifest-d/1`, committed `455788a` |
| holdout composition | ✓ — **120 cases**: W1–W7 × **12** each + **36 clean**; seed **20261112** |
| holdout `cases_sha256` | `fe09ca18…` — **re-verified** by recomputing `canonical_sha256(cases)` (D-09 hasher); matches the manifest exactly |
| tree scored | commit **`90292a4`** (`Phase E2 Module B: AIBOM import/export`), working tree clean |

Composition matches the prediction file's stated expectation ("sealed, 120 cases,
same composition as dev"). No regeneration or edit of the holdout was performed.

---

## 1. Scoring run (once)

Command (single invocation; no re-runs):

```
PYTHONPATH=src python3 -m releaseseal bench-d score \
  --manifest bench/holdout_d/manifest.json \
  --json <scratch>/holdout_score.json
```

Frozen rule packs used by the scorer (`Context.default(DATASET_PACK_IDS)`):
`dataset-hub-v1` 1.1.0, `contamination-v1` 1.1.0, `lid-v1` 1.0.0,
`license-terms-v1` 1.0.0 — the same frozen state as the committed tree `90292a4`.

**Counting rule (D-31, unchanged from GATE E1):** a case counts a class hit only
for findings with `heuristic == false` **AND** `severity != "info"`
(`gate_counted_dataset`). W8 and the `*_measured` info findings never count.

The scorer did not crash; it ran to completion on the first invocation.

### Recall + clean FP (raw counts)

| class | recall | hits / total |
|---|:--:|:--:|
| W1 | **1.000** | 12 / 12 |
| W2 | **1.000** | 12 / 12 |
| W3 | **1.000** | 12 / 12 |
| W4 | **1.000** | 12 / 12 |
| W5 | **1.000** | 12 / 12 |
| W6 | **1.000** | 12 / 12 |
| W7 | **1.000** | 12 / 12 |

- **Clean FP rate: 0.000 (0 / 36)**
- `details` (misses + false positives): **empty** — every planted class fired on
  every case; no clean case fired any counted finding.

### GATE E2 verdict

Bars (fixed, not moved): per-class recall **≥ 0.85** for every W1–W7 **AND** clean
FP **≤ 5%**.

- Recall floor 0.85: met by all seven classes (every one at 1.000).
- Clean FP ceiling 0.05: met (0.000).

**GATE E2 — PASS.**

(The scorer CLI also prints a line labelled "GATE E1 (recall ≥ 0.9, FP ≤ 0.05):
PASS" because the built-in `gate_e1` helper carries the E1 floor of 0.90. The E2
verdict above was computed by applying the fixed E2 bars (0.85 / 0.05) to the
scorer's **raw** recall/FP output rather than adding or editing a gate function,
which would have been a verifier change — see **D-45**. The measured recall
(1.000) clears both floors, so the two agree here.)

---

## 2. Predictions vs actual

### 2a. Holdout (preregistered `reports/phase-e2-predictions.md`, commit `f3b9cba`)

| class | predicted recall | measured recall | Δ (meas − pred) |
|---|:--:|:--:|:--:|
| W1 | 0.93 | 1.000 | +0.07 |
| W2 | 0.95 | 1.000 | +0.05 |
| W3 | 0.92 | 1.000 | +0.08 |
| W4 | 0.97 | 1.000 | +0.03 |
| W5 | 0.90 | 1.000 | +0.10 |
| W6 | 0.88 | 1.000 | +0.12 |
| W7 | 0.85 | 1.000 | +0.15 |

- predicted clean FP rate **0.02** → measured **0.000** (−0.02).

Every class beat its predicted recall; every prediction was in the correct
direction (all predicted ≥ the 0.85 bar). The predictions were **conservative**
on the holdout — the opposite of the optimistic Part B-D bias (§2b) and of the
model-side GATE 2 clean-FP mis-prediction. **Caveat (carried from GATE E1 /
GATE 1):** the holdout is *synthetic and co-designed* with the same W-check
vocabulary that scores it — authored by a separate session but from the shared
design, not drawn from independent real-world releases. A perfect synthetic recall
is consistent with that design and is **not** evidence of real-world recall; the
real-data behaviour is the Part B-D audit (§2b/§3), where the honest finding is
that real cards exercise almost none of this vocabulary.

### 2b. Part B-D predictions hit/miss (from `reports/phase-e2-build.md` §3.4)

Scored by the build session's audit (`audit/partbd/summary.json`), not re-run here;
carried verbatim.

| id | prediction | threshold | measured | verdict |
|---|---|:--:|:--:|:--:|
| P1 | ≥60% datasets ≥1 counted finding | 0.60 | 0.361 (13/36) | MISS |
| P2 | W1 license inconsistency in ≥25% | 0.25 | 0.000 | MISS |
| P3 | W4 detector hits in ≥15% | 0.15 | 0.194 (7/36) | **HIT** |
| P4 | W5 measured overlap >0 in ≥10% | 0.10 | 0.028 (1/36) | MISS |
| P5 | W7 declared-language problems in ≥10% | 0.10 | 0.028 (1/36) | MISS |
| P6 | W8 completeness gaps in ≥50% (signal) | 0.50 | 1.000 | **HIT** |

**2 hits, 4 misses.** The Part B-D predictions were optimistic in the direction
the model-side GATE 2 history warns about.

---

## 3. Part B-D headline summary (carried from the build report)

Live audit of **36** frozen real HF datasets (`bench/partbd/datasets.json`, frozen
at `314b2b1` before the audit). **36/36 ok, 0 errors**, $0 spend, metadata +
`dsample/1`-capped samples only; raw sample text redacted on disk (D-40), W4 values
masked (D-31).

- **13/36** datasets yielded ≥1 counted finding (non-heuristic, non-info).
- **Claim-violation stratum** (a real declaration actually violated): **321 findings,
  all from one dataset** — `wikimedia/wikipedia`'s W7 `declared_language_absent`,
  which is a **single-config sampling-coverage artifact**, not a real falsification
  (the dataset genuinely contains those languages in other configs). **No other
  dataset produced any claim violation.**
- **Measurement stratum** (info + detector hits, at sampled coverage): W4 detector
  hits 40 across 7 web-crawl corpora (`email` 29, `card_luhn` 9 — Luhn-valid-by-chance
  noise, `ipv4` 2; all masked); W5 overlap >0 on 1 dataset (`openai/gsm8k` vs its own
  source suite `gsm8k-test`, 0.502 — circular but a correct measurement); W6
  `dedup_measured` on all 19 text-sampled datasets.
- **W1 `license_unknown`** (counted): 10 datasets whose declared license is outside
  the 12-entry `license-terms-v1` table → "undeterminable", never an inferred verdict.
  **W1 `license_inconsistent`: 0** (Croissant normalization D-39 removed format-only
  artifacts; no identified LICENSE file disagreed).
- **W8 completeness gaps: 100%** (signal only) — every real card is missing ≥1
  declaration field.

**Coverage caveats (carried):** 19/36 datasets got a content sample; **17/36 have an
empty sample** (image/audio/binary corpora or configs datasets-server does not
row-serve). The content sample is a **prefix window** (`rows_per_split=200`, first 2
splits of the largest row-served config), not a full-corpus reservoir; true split
totals are the coverage denominator. The pack **never certifies absence** — all
content findings are measurements at the stated coverage. Honest reading: real
dataset cards carry almost none of the machine-readable declarations the W-checks
grade, so Module D's real-data value is **measurement at stated coverage**, not
claim falsification.

---

## 4. Module B summary (carried from `reports/phase-e2-bom.md`)

AIBOM import/export; **independent of GATE E2** (touches no holdout, no gate).

- **Importers:** CycloneDX 1.5/1.6/1.7 (`metadata.component` + `components[]`) and
  SPDX 3.0 AI (JSON-LD `@graph`); hashes normalized across formats (D-44);
  non-model/dataset components carried as kind `"other"` **and** counted in `ignored`
  (D-43); SPDX elements that map to no package counted in `unmapped`, never guessed.
- **Decidable checks** (`check="B1"`, each tested +/−): `bom_hash_mismatch` (high),
  `bom_license_mismatch` (medium), `bom_dangling_ref` (medium, pure document),
  `bom_undeclared_artifact` (medium). Anything semantic → **`unverifiable`**
  (first-class counted outcome), never a finding and never a pass.
- **Mini-bench** `bench/bom_cases.py`: 24 cases (`bom-manifest/1`, `cases_sha256`
  `312e000e…`), **exact-match 24/24 PASS** — a regression check, **not a gate**; no
  holdout.
- **Unverifiable accounting:** a BOM whose described artifacts are not in hand is
  *measured as unverifiable* (`reason ∈ {no artifact set, no matching file, no
  declared license, no comparable hash}`), not passed; a hash that **is** checked
  never also appears as unverifiable. Export → import round-trips the component set;
  all outputs byte-deterministic (D-09). $0, stdlib only, offline.

---

## 5. Per-class miss analysis

**Not applicable.** No class scored below 1.000 and the scorer reported an empty
`details` list — there were **zero missed cases** and **zero clean-case false
positives** on the holdout. There is nothing to diagnose. (Had any class been
below 1.000, this section would list the missed case ids and what each planted vs
what fired, as observed facts only.)

---

## 6. GATE E1 regression (re-run this session)

Re-run after scoring, on tree `90292a4`, to confirm nothing drifted. These are
dev-split / test-suite runs and are repeatable — unlike the once-only holdout.

- **Part A-D dev bench** — regenerated at seed **20261111** →
  `cases_sha256 0e2633a26ed15c72b585e00697c4b1f013d212a0630e214f0c9a33bc21a4ab32`
  (**byte-identical to E1**); scored: per-class recall **W1–W7 all 1.000** (12/12),
  clean FP **0.000** (0/36) → **GATE E1 still PASS**.
- **Full test suite** — `python -m pytest`: **183 passed**, offline, no network
  (141 model+dataset + 42 Module B). (The build report's "141 green" predates the
  Module B session's 42 tests, now all on this tree.)
- **Model side (bonus check)** — model GATE 1 bench (`out/bench/manifest.json`):
  V1–V7 all **1.000**, clean FP **0.000** → still PASS; model `pack/1` path
  untouched.

---

## 7. Judgment calls

One, recorded as **D-45** (GATE E2 verdict computed by applying the fixed E2 bars
to the scorer's raw output, since the frozen scorer exposes only an E1-floored
gate helper and editing it would be a verifier change). No other judgment calls
were needed: the scorer ran once without crashing, the holdout was scored as
sealed, and no deviation from the prompt was required.

---

## 8. Hard rules held

- **Holdout scored exactly once.** No re-score. No verifier change before, during,
  or after scoring. A re-score after any code change would void the measurement;
  none was warranted or performed.
- **No fabrication.** Every number here is from a command run this session
  (`bench-d score`, `bench-d generate`, `pytest`, `bench score`) or carried
  verbatim from a cited prior report. Nothing not run is reported as run.
- **Local only.** Nothing pushed, uploaded, posted, or published. Phase E3 is a
  separate, separately-confirmed step.

## Verdict

**GATE E2 = PASS** — on the sealed holdout (120 cases, `cases_sha256 fe09ca18…`,
tree `90292a4`): per-class recall 1.000 for all of W1–W7 (≥ 0.85 bar) and clean FP
0.000 (≤ 5% bar). Read with the carried caveats: the holdout is synthetic and
co-designed with the scoring vocabulary (a synthetic PASS is not real-world
recall), and the Part B-D real-data audit (2 HIT / 4 MISS; near-zero claim
violations) is the honest statement of how little of this vocabulary real dataset
cards exercise.
