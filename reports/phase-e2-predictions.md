# Phase E2 — preregistered predictions

Registered **before any E2 code change** (Step 0 of the Phase-E2 build prompt),
committed as its own commit ahead of the W1 LICENSE-file leg, the
`contamination-v1` real suites, and the Part B-D real-dataset audit. These are
locked: if a later step tempts a change, the rule is to stop and record *why* in
DECISIONS.md, never to edit this file silently (Phase-E2 hard rule 1).

Scoring: the holdout block is scored in a later sealed session (not here); the
Part B-D block is scored by **this** session's audit (`audit/partbd/summary.json`)
and the hit/miss result is reported in `reports/phase-e2-build.md`.

## Holdout (sealed, 120 cases, same composition as dev)

Authored by a separate independent session; scored once by the later scoring
session with the frozen verifier. GATE E2 bar (SPEC §9b/§E1.9 discipline):
per-class recall ≥ 0.85 for every W1–W7, clean FP ≤ 5%.

| class | predicted recall |
|---|---|
| W1 | 0.93 |
| W2 | 0.95 |
| W3 | 0.92 |
| W4 | 0.97 |
| W5 | 0.90 |
| W6 | 0.88 |
| W7 | 0.85 |

- clean FP rate: **0.02**

## Part B-D (36 real datasets, this session's audit)

Counted findings = `heuristic == false` AND `severity != "info"` (D-31). The
measurement predictions (W4/W5/W7/W8) are stated at the sampled coverage the
snapshots record; they are audit facts, not claim-violation headlines (the W8
one is explicitly signal-only).

- **≥ 60%** of datasets yield **≥ 1 counted finding** (non-heuristic, non-info)
- **W1 license inconsistency** in **≥ 25%** of datasets
- **W4 detector hits** (at sampled coverage) in **≥ 15%** of datasets
- **W5 measured overlap > 0** in **≥ 10%** of datasets
- **W7 declared-language problems** (absent or undeclared-dominant) in **≥ 10%**
- **W8 completeness gaps** in **≥ 50%** (signal only, never a headline claim)
