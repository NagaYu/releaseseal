# Phase E1 — dataset-verification core (GATE E1)

Extension program Phase E1 (Module D core): the dataset-release verifier
(`dsnapshot/1`, adapters, `dsample/1`, W1–W7 + W8 signal, Part A-D bench, `pack/2`).
Scope per `releaseseal-extension-design.md` §3 and the Phase-E1 authoring prompt.
SPEC fixed first in `SPEC.md` "Extension E1"; interpretation choices recorded as
DECISIONS D-27..D-36. **No publication, no remote operations** — local commit only.

## 1. What was built (module map)

| area | module(s) | notes |
|---|---|---|
| dataset schema | `snapshot/dschema.py` | `dsnapshot/1`, closed-vocabulary declaration extractor (D-27), Croissant subset, `validate`, shared `content_hash` |
| sampling | `snapshot/dsample.py` | `dsample/1` — per-split sha256-derived reservoir, caps, text-field selection (D-28); shared by adapters + bench |
| adapters | `snapshot/local_dataset.py`, `snapshot/hf_dataset.py` | directory + HF-dataset (injectable fetcher, offline `DatasetFixtureFetcher`) |
| checks | `verify/wchecks.py`, `verify/lid.py` | W1–W8; PII masking (D-31); contamination 13-gram; MinHash dedup; LID |
| core dispatch | `verify/core.py` | `verify()` dispatches on `schema_version`; `verify_dataset()` entry point |
| packs | `rules/packs/dataset-hub-v1.json`; `rules/build_packs.py` → `contamination-v1.json`, `lid-v1.json` | generated packs regenerate byte-identically |
| evidence | `evidence/pack.py`, `evidence/report.py` | `pack/2` for datasets (snapshot_kind); model `pack/1` byte-for-byte (D-35); PII-absence caveat in report |
| bench | `bench/generate_d.py`, `bench/score_d.py` | Part A-D generator + scorer (`bench-manifest-d/1`) |
| CLI | `cli.py` | `dsnapshot`, `bench-d generate|score`; `verify`/`pack` dispatch on schema |
| fixtures | `fixtures/hf/dataset-tiny-clean.json`, `dataset-gaps.json` | offline hf_dataset bundles |

## 2. GATE E1 — measured numbers

Part A-D dev split: **120 cases, seed 20261111**, `cases_sha256`
`0e2633a26ed15c72b585e00697c4b1f013d212a0630e214f0c9a33bc21a4ab32`.
Composition: W1–W7 × 12 (= 84) + 36 clean.

Per-class recall (counting rule D-31: `heuristic == false` AND `severity != "info"`):

| class | recall | hits |
|---|---|---|
| W1 | 1.000 | 12/12 |
| W2 | 1.000 | 12/12 |
| W3 | 1.000 | 12/12 |
| W4 | 1.000 | 12/12 |
| W5 | 1.000 | 12/12 |
| W6 | 1.000 | 12/12 |
| W7 | 1.000 | 12/12 |

Clean false-positive rate: **0.000 (0/36)**.

**GATE E1 = PASS** — per-class recall ≥ 0.90 for every W1–W7 (all 1.000), clean FP
≤ 5% (0.0%), full test suite green.

Caveat (same as GATE 1): the dev split is mutually consistent with the rules that
score it; real generalisation is Phase E2 (independent sealed holdout +
Part B-D), which this session does not author. Honest limits in §5.

## 3. Tests

`python -m pytest` → **129 passed**, offline, no network.

- Existing v1 suite: **72 tests, unmodified** (not edited; `git diff` on the
  pre-existing test files is empty). Model frozen dev `cases_sha256` `5267e1a0…`
  unchanged; model GATE 1 still PASS; model `pack/1` builds byte-for-byte (D-35,
  `test_evidence_d.py::test_model_pack_still_pack1_byte_for_byte`).
- New: **57 tests** across `test_dsnapshot.py`, `test_dsample.py`,
  `test_wchecks.py`, `test_rules_d.py`, `test_evidence_d.py`, `test_bench_d.py`,
  `test_cli_d.py` — dsnapshot schema/extraction (wrong-type → null/[]), sampling
  determinism + row/byte caps + text-field order, each W class
  (positive/negative/near-miss), **masking** (full PII values asserted absent from
  findings and report), LID separation + determinism, LID & contamination pack
  byte-identical regeneration, `pack/2` round-trip + tamper + `pack/1` regression,
  bench-d byte-identical regeneration + marker discipline + GATE E1, CLI smoke.

## 4. Regeneration checks

- `contamination-v1.json` == `serialize(build_contamination_pack())` — byte-identical.
- `lid-v1.json` == `serialize(build_lid_pack())` — byte-identical.
- Part A-D manifest regenerates byte-identically at seed 20261111.
- Model dev bench + frozen `cases_sha256` unchanged.

## 5. Deviations from the prompt / extension design (with DECISIONS ids)

All are the conservative reading required by the prompt §10 ("narrower claim
surface, stricter determinism; record it; do not silently widen scope"):

- **D-29 — W1 LICENSE-file identification leg is silent.** The prompt pins
  identification "by the license-terms table's file-fingerprint entries" but also
  requires `license-terms-v1` be **reused unchanged**; the shipped pack has no such
  entries and editing it would break the frozen model Part B reproducibility and
  the `pack/1` byte-for-byte guarantee. So W1 resolves only declared-vs-croissant
  and declared-in-table. The bench plants W1 through those two legs; recall 1.000.
- **D-30 — W3 declared-total-size leg is silent.** The closed declaration
  vocabulary (§E1.1.1) carries no declared size surface, so there is nothing to
  compare; W3 fires via missing/undeclared/row-count. Row facts use the file→split
  name association (exact for bench).
- **D-31 — dataset counting rule.** Scorer/gate count `heuristic == false` AND
  `severity != "info"`; this excludes W8 and the `contamination_measured` /
  `dedup_measured` info measurements, as the prompt's §7 scorer rule requires.
- **D-36 — near-miss clean `pii:"present"` cases use detector-negative content.**
  A clean case must raise no counted finding, and `pii_detected` (medium) counts;
  so the truthful-disclosure clean cases declare `pii:"present"` with
  detector-negative text. The honest-disclosure semantics (present + a hit →
  `pii_detected` medium, never falsification) are proven directly in a unit test
  (`test_w4_present_disclosure_is_medium_not_falsification`), not as a bench clean.

Other recorded pins (not deviations, just fixed choices): D-27 (extraction
wrong-type → empty), D-28 (`dsample/1` algorithm), D-32 (W5 normalization +
contamination builder), D-33 (W6 MinHash construction), D-34 (`lid-v1`
construction + W7), D-35 (`pack/2` vs model `pack/1`).

## 6. Honest limitations (for Phase E2)

- **No holdout, no Part B-D in E1** (explicitly out of scope): GATE E1 is a
  co-designed-synthetic gate, exactly like GATE 1. The E1 model-side precedent
  (GATE 2 FAIL) is the reminder that a sealed independent holdout is the real
  test; E2 must author one with preregistered predictions.
- **W1 LICENSE-file leg and W3 size leg are inert by construction** (D-29/D-30) —
  real coverage of those is a future rule-pack question, not a code bug.
- **LID is a dependency-free char-n-gram classifier over short seed paragraphs**:
  strong on well-separated scripts and the bench's own vocabulary; it is a pinned
  measurement instrument, not a production LID. Confidence floor (margin 1.0,
  sum-of-logprob) sends genuinely short/ambiguous rows to `und`.
- **Content checks run on the pinned sample only** — the pack never certifies
  absence of PII/contamination/dedup; the report states this.

**Fabrication of results is prohibited** — every number above was produced by the
committed code in this session (`pytest`, `bench-d score`); nothing was hand-set.
