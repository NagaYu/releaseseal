# ReleaseSeal — Phase 2 report & GATE 2 self-assessment

Date 2026-11-08. Public name **ReleaseSeal** (was codename ModelPass). Local-only,
$0, deterministic. Part B uses the HF API for **metadata only** (no weight bytes).

## 1. GATE 2 self-judgment — **FAIL**

Criterion (Phase 2 prompt / SPEC §9b): on the sealed independent holdout, scored
once with the frozen verifier, per-class recall ≥ 0.85 for every V1–V7 **and**
clean FP ≤ 5%.

The sealed holdout (84 cases, `cases_sha256` `2dd678fd…`, authored by a separate
session from the spec alone) was delivered and **scored exactly once** with the
frozen verifier (D-17 fixes held; no tuning, no re-score). No manifest value-shape
conversion was needed — the holdout's `bench-manifest/1` format matched the
scorer directly (D-16).

| class | recall | | class | recall |
|---|---|---|---|---|
| V1 | **1.000** (8/8) | | V5 | **0.750** (6/8) |
| V2 | **1.000** (8/8) | | V6 | **0.500** (4/8) |
| V3 | **1.000** (8/8) | | V7 | **0.875** (7/8) |
| V4 | **1.000** (8/8) | | **clean FP** | **1.000 (28/28)** |

**GATE 2: FAIL** — recall floor missed on V5 (0.75) and V6 (0.50), and clean FP is
**100%** vs the ≤5% ceiling.

**V3 multi-level breakdown (the Phase-2 focus): recall 1.000 across all subtypes**
— 4/4 grandparent-only, 2/2 unknown-intermediate, 2/2 direct. The recursive
lineage walk (D-14) generalises perfectly to independently-authored multi-level
chains; this part of Phase 2 succeeded.

### Why it failed — overfitting the independent holdout exposed

GATE 1's dev clean/planted cases were **co-designed with the checks** (same
session), so dev clean FP was 0. The independent holdout, authored without seeing
the implementation, phrases cards naturally — and the frozen heuristics are too
rigid to match:

- **clean FP 100% — V4 keyword brittleness (26/28) + V2 tied-embedding (2/28).**
  The gpai-eu V4 rule pack matches *specific phrasings*; the holdout's competent
  but differently-worded documentation (e.g. no literal "testing process",
  "inputs and outputs" vs the pack's "input and output", no "distribution
  channel" section) registers as missing Annex items on every clean card. Two
  tied-embedding clean cards also trip V2 param_mismatch (the D-17 #1 estimator
  bug, now confirmed on independent data).
- **V6 0.50** — the prose eval-claim detector only matches `Benchmark: number`
  lines; the holdout's natural-sentence claims ("the model achieves 88.0 on
  GSM8K", "On MMLU the model scores 72.0") are not parsed. (model-index-vs-
  result-file and internal-conflict cases *were* caught, 4/8.)
- **V5 0.75** — two eval-source-drift cases encode the stale source in
  `result_files`, which V5 does not read (it checks card/model-index revisions
  and `as_of`/`valid_until` dates, all caught, 6/8).
- **V7 0.875** — one case references a chat-template file that is absent; V7 flags
  a missing chat template only for models tagged chat/instruct, so it misses this
  (7/8).

This is the intended function of a sealed holdout: GATE 1 (co-designed) passing
while GATE 2 (independent) fails is the signature of overfitting, surfaced
honestly rather than hidden. The decisive weakness is **V4's keyword matching**,
which must become robust to phrasing before a public audit; the numbers above
stand, unmodified, against the frozen code.

## 2. Steps 0–1: rename + audit-note closure (self-eval)

- **Step 0 — rename ModelPass → ReleaseSeal (D-13): done.** Package dir, pyproject,
  CLI name, `hf_live` User-Agent (the audit's third literal), and doc product
  names updated; codename history preserved in DECISIONS/STATUS. Verified: all
  tests green and the dev bench regenerates **byte-identically** (`cases_sha256`
  `5267e1a0…` unchanged), proving the name never leaked into bench data.
- **Step 1 — the four Phase-1 audit notes: closed.**
  1. *Lineage depth (closed).* The `hf` adapter now resolves `base_model`
     recursively (depth cap 8 + cycle guard) and flattens all ancestors into the
     snapshot; V3 walks every ancestor and names the violating one (`subject`).
     New `dev_ext` manifest adds grandparent/unknown-intermediate/deep-attribution/
     multi-parent/deep-clean cases. On `dev_ext`: V3 recall **1.000**, clean FP
     **0.000**, **lineage-walk accuracy 1.000 (24/24)**. A multi-repo offline
     fixture proves a grandparent (depth-2) violation is detected.
  2. *Fixtures (closed).* Real recorded bundles for `hf-internal-testing/
     tiny-random-gpt2` and `prajjwal1/bert-tiny` (metadata only) added alongside
     the authored ones; tests parse them offline.
  3. *Negatives (closed).* Per-class targeted negative tests added (each check has
     a boundary case that must not fire).
  4. *V8 (closed).* `fingerprints-v1` → v1.1.0 seeds `known_bases` from real base
     configs (pythia-70m, Qwen2-0.5B, phi-2); V8 now fires on real config data
     with the shipped pack (test proves it, still signal-only / never gate-counted).

## 3. Part B — measured vs pre-registered

Full results: `reports/partb.md`. 40 models, pinned revisions, **0 fetch errors,
0 zero-finding models**, all reported. Occurrence (share with ≥1 gate-counted
finding):

| class | predicted | measured | verdict |
|---|---|---|---|
| V4 documentation gaps | 85–100% | **100%** | hit |
| V2 architecture & scale | 5–20% | **50%** | miss (under-predicted) |
| V6 eval inconsistency | 20–45% | 15% | near-miss |
| V7 completeness | 10–30% | 2.5% | miss |
| V3 license lineage | 40–70% | **0%** | miss (over-predicted) |
| V1 artifact–record | 5–20% | 0% | ~within |
| V5 staleness/drift | 5–20% | 0% | ~within |

**Honest reading (detail in `reports/partb.md` §4):**
- **V4 (100%) is the real signal** — every card is missing Annex XI/XII/CoP items
  (training-content summary, copyright policy, energy, compute). Genuine, with
  per-field evidence.
- **V2 (50%) is mostly ReleaseSeal false positives**, not model defects: the
  parameter estimate overcounts tied-embedding models (gpt2/opt), the claim
  extractor misreads training-token counts (t5 "623b") and sibling-model sizes
  (Yi "34B"), and the context check ignores `rope_theta` (Yi). Recorded as D-17.
- **V6/V7** likewise include false positives (hyperparameters read as eval claims;
  `spm.model` not recognised as a tokenizer). D-17.
- **V3 (0%)** — only 3/40 cards declare `base_model` at all, and those resolve to
  compatible same-org parents; the recursive walk works, there was little declared
  lineage to walk. My "most surprising" prediction (gated-ancestor `license_unknown`
  dominating) did not occur.

The two large prediction misses (V2 over-firing, V3 non-occurrence) are reported
as-is, not reframed.

## 4. Holdout — scored once (GATE 2 = FAIL; detail in §1)

Delivered at `~/Desktop/Claude code/ModelPass-holdout/` (84 cases, seed 31415926,
`cases_sha256` `2dd678fd…`), scored **once** with the frozen verifier; no
value-shape conversion was needed (formats matched). Aggregates saved to
`audit/holdout/score.json` (scores only — no holdout cases imported into the
repo). Result: V1–V4 recall 1.000, V5 0.750, V6 0.500, V7 0.875, clean FP 1.000
→ **FAIL**. V3 multi-level recall 1.000 across all subtypes.

### Holdout vs pre-registered holdout predictions

My pre-registered guesses (`reports/phase2-predictions.md`) were **too
optimistic** — honestly, a miss:

| | predicted | measured |
|---|---|---|
| clean FP | 0–8% | **100%** |
| V6 recall | 0.82–0.95 | **0.50** |
| V5 recall | 0.88–1.00 | 0.75 |
| V4 recall | 0.82–0.95 | 1.00 |
| GATE 2 | "more likely PASS" | **FAIL** |

I predicted V4/V6 as the weakest *recall* classes; the real killer was V4
*precision* (clean FP), which I did not foresee — I assumed clean cards would
satisfy the keyword checks, exactly the co-design assumption the holdout broke.

## 5. Tests & known weaknesses

- **52 tests, all passing**, offline, no weight bytes (`python3 -m pytest -q`).
  New since Phase 1: recursive lineage (recursion, depth cap, cycle guard,
  unreachable-ancestor, grandparent detection), `dev_ext` lineage-walk, real
  fixtures, per-class negatives, V8-on-real-data.
- Frozen dev split unchanged (`cases_sha256` `5267e1a0…`); `dev_ext` is additive.
- Part B evidence packs re-verify offline (`verify-pack`), 40/40.

**Known weaknesses (honest), to fix before any gate re-attempt or Phase-3 audit:**
*From Part B (D-17):*
1. Param estimate overcounts tied-embedding models. *(GATE 2 confirmed: 2 clean FPs.)*
2. Param-claim extractor grabs training-token / sibling-model numbers from prose.
3. Context check ignores `rope_theta`-based extension.
4. V6 unsourced-claim regex matches hyperparameters / training-curve values.
5. V7 tokenizer detection misses `spm.model` and other SPM variants.

*Newly decisive from GATE 2 (D-18):*
6. **V4 keyword matching is phrasing-brittle → 100% clean FP on independent
   cards.** The gpai-eu pack must recognise Annex items by meaning/synonyms (or a
   structured card schema), not fixed substrings. This is the top blocker.
7. V6 prose detector only parses `Benchmark: number` lines, not natural-sentence
   claims (holdout V6 recall 0.50).
8. V5 ignores `result_files`-recorded source checkpoints (holdout V5 recall 0.75).
9. V7 misses chat-template-*file* references for non-chat-tagged models.

GATE 1 (synthetic, co-designed) stays PASS; GATE 2 (independent holdout) FAILS —
the honest signature of overfitting. **The fixes above were held per instruction;
the GATE 2 numbers stand against frozen code.** What generalised cleanly: V1, V2
(planted), V3 including all multi-level lineage, and V4 *recall*.

## 6. Reproduce

```bash
python3 -m pytest -q
PYTHONPATH=src python3 -m releaseseal bench generate --seed 0 --ext -o out/bench
PYTHONPATH=src python3 -m releaseseal bench score --manifest out/bench/manifest.json
PYTHONPATH=src python3 -m releaseseal bench score --manifest out/bench/manifest_ext.json  # lineage-walk
# Part B (network, metadata only):
PYTHONPATH=src python3 bench/partb/run_partb.py --models bench/partb/models.json --out audit/partb
# GATE 2: score the sealed holdout once with the frozen verifier (external manifest):
PYTHONPATH=src python3 -c "import json;from releaseseal.bench import score,gate1;\
m=json.load(open('/Users/nagaoyuta/Desktop/Claude code/ModelPass-holdout/manifest.json'));\
s=score(m);print({k:round(v,3) for k,v in s['recall'].items()},'FP',round(s['clean_fp_rate'],3),\
gate1(s,recall_floor=0.85,fp_ceiling=0.05)['pass'])"
```

GATE 2 is now measured: **FAIL** (clean FP 100%, V5/V6 recall below 0.85). The
decisive fix is V4 phrasing-robustness; fixes are held per instruction. Stopping
here for audit and the publication decision, per the Phase 2 prompt. No
publish/push/upload performed.
