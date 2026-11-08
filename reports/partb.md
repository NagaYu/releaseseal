# ReleaseSeal — Part B: real-release audit report

**Not a compliance certification.** Each finding states an inconsistency between a release's *own documentation* and its artifacts (or ReleaseSeal's heuristic estimate), with an evidence pointer. It is not a legal verdict, and `license_unknown`-style undeterminable results are never asserted as violations. Where a finding is a limitation of ReleaseSeal's heuristics rather than a real inconsistency in the model, this report says so explicitly (see §4).

## 1. Method

- Target list frozen in `bench/partb/models.json`: **40 models** across 10+ organisations and 10 declared-license families, each at a **pinned revision** (not changed after the run, D-16).
- Snapshots fetched via the `hf` adapter — **metadata + small files only, no weight bytes** — on **2026-11-08**. Verified with the **frozen** code and rule packs (`fingerprints-v1`=1.1.0, `gpai-eu-v1`=1.0.0, `hub-metadata-v1`=1.0.0, `license-terms-v1`=1.0.0).
- Evidence packs + snapshots for every model saved under `audit/partb/`. Result: **40/40 snapshotted with 0 errors**, **0 models with zero findings** — all 40 reported below (no cherry-picking).

## 2. Per-class occurrence (share of models with ≥1 gate-counted finding)

| class | occurrence | models |
|---|---|---|
| V1 artifact–record | **0.0%** | 0/40 |
| V2 architecture & scale | **50.0%** | 20/40 |
| V3 license lineage | **0.0%** | 0/40 |
| V4 documentation gaps | **100.0%** | 40/40 |
| V5 staleness/drift | **0.0%** | 0/40 |
| V6 eval inconsistency | **15.0%** | 6/40 |
| V7 completeness | **2.5%** | 1/40 |

Finding-code totals across all models: `doc_gap`×376, `param_mismatch`×18, `unsourced_claim`×10, `context_mismatch`×3, `tokenizer_missing`×1.

## 3. Per-model results (all 40)

| # | model | license | findings | by class |
|---|---|---|---|---|
| 1 | `Qwen/Qwen2.5-0.5B` | apache-2.0 | 14 | V2×1 V4×12 V6×1 |
| 2 | `Qwen/Qwen2.5-0.5B-Instruct` | apache-2.0 | 15 | V2×1 V4×12 V6×2 |
| 3 | `Qwen/Qwen2.5-Coder-0.5B` | apache-2.0 | 13 | V4×12 V6×1 |
| 4 | `Qwen/Qwen2.5-1.5B` | apache-2.0 | 13 | V4×12 V6×1 |
| 5 | `microsoft/phi-2` | mit | 10 | V2×1 V4×9 |
| 6 | `microsoft/Phi-3-mini-4k-instruct` | mit | 9 | V4×9 |
| 7 | `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | apache-2.0 | 13 | V4×13 |
| 8 | `HuggingFaceTB/SmolLM2-135M` | apache-2.0 | 9 | V4×9 |
| 9 | `HuggingFaceTB/SmolLM2-360M` | apache-2.0 | 10 | V2×1 V4×9 |
| 10 | `HuggingFaceTB/SmolLM-1.7B` | apache-2.0 | 13 | V2×1 V4×12 |
| 11 | `stabilityai/stablelm-2-1_6b` | other | 8 | V4×8 |
| 12 | `stabilityai/stablelm-3b-4e1t` | cc-by-sa-4.0 | 7 | V4×7 |
| 13 | `EleutherAI/pythia-70m` | apache-2.0 | 8 | V4×8 |
| 14 | `EleutherAI/pythia-160m` | apache-2.0 | 9 | V2×1 V4×8 |
| 15 | `EleutherAI/gpt-neo-125m` | mit | 9 | V2×1 V4×8 |
| 16 | `bigscience/bloom-560m` | bigscience-bloom-rail-1.0 | 10 | V4×7 V6×3 |
| 17 | `bigscience/bloomz-560m` | bigscience-bloom-rail-1.0 | 11 | V4×11 |
| 18 | `facebook/opt-125m` | other | 10 | V2×1 V4×9 |
| 19 | `facebook/opt-1.3b` | other | 10 | V2×1 V4×9 |
| 20 | `Salesforce/codegen-350M-mono` | bsd-3-clause | 9 | V4×9 |
| 21 | `google/flan-t5-base` | apache-2.0 | 8 | V2×1 V4×7 |
| 22 | `google-t5/t5-small` | apache-2.0 | 7 | V2×1 V4×6 |
| 23 | `distilbert/distilbert-base-uncased` | apache-2.0 | 8 | V4×8 |
| 24 | `google-bert/bert-base-uncased` | apache-2.0 | 8 | V4×8 |
| 25 | `FacebookAI/roberta-base` | mit | 8 | V4×8 |
| 26 | `openai-community/gpt2` | mit | 9 | V2×1 V4×8 |
| 27 | `openai-community/gpt2-medium` | mit | 6 | V4×6 |
| 28 | `distilbert/distilgpt2` | apache-2.0 | 7 | V4×7 |
| 29 | `deepseek-ai/deepseek-coder-1.3b-base` | other | 13 | V2×1 V4×12 |
| 30 | `01-ai/Yi-6B` | apache-2.0 | 13 | V2×2 V4×11 |
| 31 | `tiiuae/falcon-rw-1b` | apache-2.0 | 10 | V2×1 V4×9 |
| 32 | `tiiuae/falcon-7b` | apache-2.0 | 9 | V4×9 |
| 33 | `bigcode/starcoder2-3b` | bigcode-openrail-m | 11 | V2×1 V4×10 |
| 34 | `sentence-transformers/all-MiniLM-L6-v2` | apache-2.0 | 11 | V2×1 V4×10 |
| 35 | `microsoft/deberta-v3-base` | mit | 16 | V2×1 V4×12 V6×2 V7×1 |
| 36 | `cardiffnlp/twitter-roberta-base-sentiment-latest` | cc-by-4.0 | 14 | V2×1 V4×13 |
| 37 | `mistralai/Mistral-7B-v0.1` | apache-2.0 | 13 | V4×13 |
| 38 | `google/gemma-2-2b` | gemma | 10 | V4×10 |
| 39 | `meta-llama/Llama-3.2-1B` | llama3.2 | 6 | V4×6 |
| 40 | `allenai/OLMo-1B-hf` | apache-2.0 | 11 | V2×1 V4×10 |

## 4. What the findings mean (honest reading)

The only signal that is robust at this scale is **V4 (100%)**. V2/V6/V7 here are
**dominated by limitations of ReleaseSeal's heuristics on real cards**, not by
real inconsistencies in the models. Stating this plainly is the point of auditing
real releases rather than only synthetic ones.

**V4 — documentation gaps (100%, 376 findings): real.** Every audited card is
missing one or more Annex XI / Annex XII / CoP items — most commonly the
training-content summary (Art. 53(1)(d)), copyright policy (Art. 53(1)(c)),
energy consumption, and training compute. These are genuine, with a card-field
evidence pointer each. This is the finding that matters: the paperwork these
releases would need for the EU AI Act is, as of the captured revision, absent.

**V2 — architecture & scale (50%): mostly heuristic false positives.** Three
distinct ReleaseSeal weaknesses, evidenced:
- *Parameter estimate overcounts tied-embedding models.* `gpt2` card says 124M
  (correct, embeddings tied); ReleaseSeal estimates 162M because the config does
  not set `tie_word_embeddings`, so the untied estimate adds a second vocab×hidden
  matrix. Same for `facebook/opt-125m`. → estimator bug, not a model defect.
- *Claim extractor grabs the wrong number from prose.* `google-t5/t5-small` →
  "623b" extracted from a **training-token** count, read as 623 **billion
  parameters** (the model is 60M). `01-ai/Yi-6B` → "34B" extracted from a mention
  of the **sibling** model Yi-34B (ReleaseSeal's own estimate, 6.06B, is correct).
- *Context check ignores `rope_theta`-based extension.* `01-ai/Yi-6B` advertises
  200K context via a large `rope_theta` (5e6) while `max_position_embeddings` is
  4096; ReleaseSeal only exempts a `rope_scaling` dict, so it false-fires.

**V6 — eval inconsistency (15%): partly false positives.** The prose-claim
extractor matches any `word: number` line, so it flags **hyperparameters**
(`microsoft/deberta-v3-base`: `num_gpus: 8`, `batch_size: 8`) and **training-curve
values** (`bloom-560m`: training/validation loss, perplexity) as unsourced eval
claims. These are not benchmark claims; the check is too broad.

**V7 — completeness (2.5%): a false positive.** `microsoft/deberta-v3-base` ships
an SPM tokenizer as `spm.model`, which is not in ReleaseSeal's tokenizer-file list
(`tokenizer.json`/`tokenizer.model`/`vocab.json`/`spiece.model`) → spurious
`tokenizer_missing`.

**V3 — license lineage (0%): real, and informative.** Only 3/40 cards declare a
`base_model` in their Hub metadata at all, and those three resolve to
same-licence parents (apache/mit) → no violation. The recursive walk works (it
resolved those parents); there was simply little declared lineage to walk. This
says something true about the ecosystem: declared machine-readable lineage is
rare, so a lineage auditor's yield depends on adoption of the `base_model` field.

**V1, V5 — 0%.** No artifact/record hash conflicts and no stale `as_of`/revision
drift surfaced in this set.

## 5. Vs pre-registered predictions (`reports/phase2-predictions.md`)

| class | predicted | measured | verdict |
|---|---|---|---|
| V4 | 85–100% | 100% | **hit** |
| V3 | 40–70% | 0% | **miss** (over-predicted — assumed gated-ancestor `license_unknown` would dominate; in fact few cards declare lineage) |
| V6 | 20–45% | 15% | near-miss (below range; and partly false positives) |
| V7 | 10–30% | 2.5% | miss (over-predicted) |
| V2 | 5–20% | 50% | **miss** (under-predicted — did not anticipate estimator/extractor false positives) |
| V1 | 5–20% | 0% | within/near |
| V5 | 5–20% | 0% | within/near |

The "most surprising" pre-registered guess (V3 driven by gated-ancestor
`license_unknown`) did **not** happen — the real surprise is that cards rarely
declare lineage at all, and that V2's heuristics over-fire on real configs. Both
misses are recorded honestly rather than reframed.

---

## Errata (fix-completion round, appended; original text above unchanged)

Two corrections to §4's analysis, confirmed by direct inspection of the saved
Part B v1 snapshots:

1. **`google-t5/t5-small` "623b" was NOT a training-token count.** It is the
   prefix of a GitHub **camo image-URL hash** in the card
   (`https://camo.githubusercontent.com/623b4dea0b653f2ad3f36c71ebfe749a677ac0a1/…`).
   The old extractor matched the bare `623b` substring. The fix (require a
   parameter context, D-17 #2) excludes it regardless of what the digits were;
   the comment in `cardparse.py` and the Part B §4 wording are corrected here.

2. **The two gated models' inspection surface was narrow.** `google/gemma-2-2b`
   and `meta-llama/Llama-3.2-1B` are gated, so their `config.json` could not be
   fetched (`config_present = False` in the saved snapshots). Findings on them in
   v1 were based on card metadata only, without the config facts V2/V7 rely on —
   a narrower check than for open models, not a clean bill.

3. **The clean V2 false positives were gated-MLP (FFN), not tied embeddings.**
   See DECISIONS.md "Correction to D-18/D-19" and D-21. The tied/untied fix is
   real but separate (it addresses Part B's gpt2/opt); the holdout cases were
   `gpt_neox` under-counted as a plain MLP.

The fixed-verifier re-run of all 40 models is reported separately in
`reports/partb-v2.md`; the original GATE 2 = FAIL in `reports/phase2.md` stands
unchanged.
