# ReleaseSeal v2 — release notes (draft)

> Draft for the GitHub v2 release. Not posted; publication is owner-confirmed,
> item by item. Numbers are the audited E1/E2 figures only; framing rules apply.

## ReleaseSeal v2 — datasets + AIBOM

ReleaseSeal v1 verified **model releases** (documentation + declared metadata vs
artifacts; V1–V8). v2 widens the same offline, deterministic engine along two axes,
with no new product, name, or repo.

### New — Dataset releases (Module D)

The same claims-vs-artifacts verification for **dataset releases** (a Hugging Face
dataset repo at a pinned revision, or a local dataset directory). Checks W1–W7
(deterministic) + W8 (signal). **Every W-check binds only to structured
declarations** (card YAML, Croissant, LICENSE files, tags) — never prose. Content
checks (W4–W7) run on a pinned deterministic sample (`dsample/1`) and cite their
coverage; the pack never certifies absence.

- **GATE E1 = PASS** (dev synthetic, 120, seed 20261111): recall 1.000 W1–W7,
  clean FP 0.000.
- **GATE E2 = PASS** (sealed holdout, 120, seed 20261112): recall 1.000 W1–W7,
  clean FP 0.000, beating every preregistered prediction (0.85–0.97). **Caveat:**
  the holdout is synthetic and co-designed with the scoring vocabulary — a perfect
  synthetic recall is **not** a real-world recall estimate.
- **Headline — Part B-D real audit (36 datasets):** a **measurement** result, not a
  falsification result. **W8 completeness gaps 100%** (every card misses ≥1
  declaration field); claim violations ≈ 0 (`license_inconsistent` 0/36,
  `license_unknown` 10/36); W4 PII detector hits (format only, masked: email 29,
  card_luhn 9, ipv4 2) on 7/36 web-crawl corpora — the card_luhn hits are
  Luhn-valid-by-chance strings, not confirmed cards; coverage 19/36 content-sampled
  (17/36 binary / not row-served); 13/36 with ≥1 counted finding. Preregistered
  predictions **2 HIT / 4 MISS** (disclosed). Real cards carry almost none of the
  machine-readable declarations the W-checks grade, so the module's real-data value
  is measurement at stated coverage.

### New — AIBOM import/export (Module B)

CycloneDX **1.5/1.6/1.7** and **SPDX 3.0 AI** documents become first-class inputs
and outputs. Four decidable checks (`bom_hash_mismatch`, `bom_license_mismatch`,
`bom_dangling_ref`, `bom_undeclared_artifact`); **`unverifiable` is a first-class,
counted outcome** (a BOM whose artifacts are not in hand is measured as
unverifiable, never silently passed). Export emits a CycloneDX 1.6 ML-BOM from any
evidence pack and round-trips. Mini-bench **24/24 exact** — a regression check, not
a gate.

### Unchanged (v1 disclosures stand verbatim)

- Model Part B (40 public models) remains the model-side headline; per-item
  missing-documentation counts unchanged.
- Model gate history unchanged: **GATE 1 PASS; GATE 2 FAIL ×3** (always V4 clean
  false positives; recall V1–V7 1.000 on the final set). Published as-is under the
  pre-recorded stop rule. V4 remains a screening signal.

### Engineering

- Full test suite **183 passed**, offline, $0 (model + dataset + BOM).
- New rule packs: `dataset-hub-v1`, `contamination-v1` (13-gram hashes only),
  `lid-v1`; `license-terms-v1` byte-unchanged; model `pack/1` byte-for-byte.
- Evidence pack `pack/2` (backward-readable); CLI gains `dsnapshot`, `bench-d`,
  `bom import|export`.
- All Rights Reserved; the only contact route is the portfolio. Sealed holdout
  cases are never published (only aggregates).
