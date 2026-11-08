# ReleaseSeal — fix round (post-GATE-2) completion report

Date 2026-11-08. Records the heuristic-fix round and the post-audit completion
items. **The original GATE 2 = FAIL stands unchanged in `reports/phase2.md`;**
this document does not re-judge it. No scoring of the canonical re-gate holdout
(`ModelPass-holdout-v2`) is done here — that is a separate round.

## 1. Fix items

### Original remediation (committed `8ec864c`; D-17/D-18)
- V2 param estimate tied/untied range (gpt2/opt); parameter-context claim
  extraction; `rope_theta` context exemption.
- V4 phrasing-robust matching (synonyms + normalise + depluralise).
- V5 reads `result_files` source checkpoints; V6 natural-sentence claims +
  hyperparameter stoplist; V7 `spm.model` + chat-template-file reference.

### Completion round (this document; D-20/D-21/D-22, + corrections)
1. **Gated-MLP FFN (D-21).** The real cause of the holdout clean V2 false
   positives was FFN structure, **not** tied embeddings (correction appended to
   D-18/D-19). `estimate_params` chooses gated (3-matrix) vs plain (2-matrix) MLP
   deterministically by `model_type`; `gpt_neox` was missing and is added. The
   authoritative gated set is recorded in D-21.
2. **Rule-pack versioning (D-20).** `gpai-eu-v1.json` restored to **1.0.0** (so
   frozen Part B v1 reproduces with pack 1.0.0); broadened rules ship as **new**
   `gpai-eu-v2.json` (2.0.0); verifier default switched to v2.
3. **Provider-document items (D-22).** `cop.copyright_policy` and
   `cop.training_content_summary` now need a substantive phrase OR a card
   reference field — a bare word ("copyright") no longer satisfies.
4. **Records:** this report, `partb-v2.md`, the `partb.md` Errata, DECISIONS
   corrections, the `cardparse.py` comment (t5 "623b" = image-URL hash, not
   tokens), and the `fixtures/hf/README.md` path fix.

## 2. Before / after

### dev + dev_ext (GATE 1) — unchanged, still green
- dev per-class recall **all 1.000**, clean FP **0.000**; `cases_sha256`
  `5267e1a0…` **unchanged** (frozen split untouched).
- dev_ext V3 recall 1.000, clean FP 0.000, **lineage-walk 1.000**.
- Test suite: **66 passing**, offline (was 61; +5 regressions: gated-MLP,
  provider-doc bare-word/phrase/reference, pack versions).

### Disclosed holdout v1 — regression re-score (fixed verifier)
Using the un-sealed v1 as regression data only (not a gate):

| class | at GATE 2 (frozen) | after fixes |
|---|---|---|
| V1–V4 | 1.000 | 1.000 |
| V5 | 0.750 | **1.000** (result_files) |
| V6 | 0.500 | **0.750** (natural claims) |
| V7 | 0.875 | **1.000** (spm/template) |
| clean FP | 1.000 | 1.000 |

The clean V2 false positives are **gone** (gated-MLP fix). Clean FP is still
100%, now entirely from `xi.testing_process` (28) and `cop.distribution` (28) —
items v1's clean cards **genuinely omit**. Testing-process is in the authoring
item spec (v1 authoring was simply incomplete); **distribution channels is NOT
in the item spec** yet is gate-counted — the spec/pack mismatch flagged in
`reports/phase2-fix-predictions.md` as the dominant re-gate risk. Not chased here
(v1 is retired; tuning to it would be overfitting).

### Part B v1 → v2 (full detail in `reports/partb-v2.md`)
40 real models, re-snapshotted + fixed verifier:
- **doc_gap (V4) 376 → 297** — phrasing false gaps removed (downstream 40→11,
  distribution 37→18, training-process 13→0); residual are genuine Annex gaps
  (copyright policy 40/40, training-content summary 40/40, compute 38, energy 33).
- **V2 20 → 16 models** — context_mismatch 3→0; gpt2/opt and t5-hash FPs gone.
- **V6 unsourced 10 → 5**; **V7 tokenizer_missing 1 → 0**.

## 3. Remaining weaknesses (honest)

1. **Param-claim extraction on *family* cards.** The 16 residual Part B V2
   findings are cards that list a whole suite's sizes in a parameter context
   ("72 billion parameters", "175B", "34B model"); the extractor grabs a sibling
   model's size. Requiring a parameter context fixed bare names and URL hashes
   but not this. A structured `params` field or per-model disambiguation is the
   next step.
2. **`cop.distribution` spec/pack mismatch** — gate-counted but not in the
   authoring item spec; the top re-gate clean-FP risk (D-22 note,
   phase2-fix-predictions §clean FP). Surfaced for the owner, not resolved here.
3. **Gated-family over-count risk (D-21)** — a genuinely plain-MLP model using a
   gated `model_type` could be over-counted (V2-direction).
4. **Encoder models** — the decoder-oriented param estimate is wrong for
   encoder/encoder-decoder (deberta/t5); out of the GPAI decoder-LM target but
   present in Part B.
5. **V6 prose extraction remains heuristic** (recall risk on unusual phrasings).

## 4. Status

Completion items 1–5 done; 66 tests green; GATE 1 held; `reports/phase2.md`
GATE 2 = FAIL unchanged; re-gate predictions pre-registered and committed
(`f460693`). Stopped before scoring, per the completion prompt. The canonical
re-gate set (`ModelPass-holdout-v2`) and scoring instructions come separately.

---

## Addendum — D-23 (gpt_neox reverted to plain MLP)

Correcting D-21: real GPT-NeoX (Pythia, GPT-NeoX-20B) uses a **plain** 2-matrix
MLP, so `gpt_neox` was removed from the gated families — the verifier models the
real architecture, not the v1 author's counting convention (public fact, not
sealed data). GATE 1 unaffected (dev uses `llama`; dev/dev_ext numbers and dev
`cases_sha256` unchanged); tests green.

**Holdout v1 regression V2 clean FP: 0 → 2.** The two clean `gpt_neox` cases
(0062/0067) state a *gated* (3-matrix) parameter count for a plain-MLP
architecture; the corrected verifier estimates them as plain, so the claims now
mismatch. This is an **author counting-convention deviation**, not a verifier
regression — the §2 "holdout v1 regression" table's "clean V2 false positives are
gone" line is superseded by this addendum (the removal was specific to the
mis-attributed tied-embedding theory; the real cause and correct behaviour are
D-23). The §3 remaining-weakness #3 (gated-family over-count risk) is **resolved**.

---

## GATE 2 re-gate (holdout v2, scored once)

Scored the designated holdout `ModelPass-holdout-v2` (`cases_sha256`
`1419e1de…`, 84 cases) **exactly once** with the frozen verifier at commit
`0ee34bf` (working tree clean; no tuning, no re-runs). Aggregates only in
`audit/holdout-v2/score.json`; no holdout cases imported into the repo.

| class | recall | | class | recall |
|---|---|---|---|---|
| V1 | **1.000** (8/8) | | V5 | **1.000** (8/8) |
| V2 | **1.000** (8/8) | | V6 | **0.750** (6/8) |
| V3 | **1.000** (8/8) | | V7 | **1.000** (8/8) |
| V4 | **1.000** (8/8) | | **clean FP** | **1.000 (28/28)** |

**Re-gate verdict: FAIL** — recall floor 0.85 missed on V6 (0.750), and clean FP
is **100%** vs the ≤5% ceiling.

**V3 multi-level: recall 1.000 across all subtypes** — 4/4 grandparent-only, 2/2
unknown-intermediate, 2/2 direct. The recursive lineage walk generalises to a
second, independently-authored set.

### Why clean FP is 100% — a spec/pack coverage mismatch (not a phrasing-only bug)

Clean V4 gaps by item across the 28 clean cards:

| item | clean cards flagged | in authoring item spec? |
|---|---|---|
| `xi.compute` | 28 | **no** |
| `xi.energy` | 28 | **no** |
| `xi.testing_process` | 23 | yes (phrasing miss) |
| `xii.downstream_integration` | 21 | yes (phrasing miss) |
| `xii.acceptable_use` | 17 | yes (phrasing miss) |
| `xii.io_modality` | 17 | yes (phrasing miss) |
| `xi.data_summary` | 15 | yes (phrasing miss) |
| `xii.io`/`xi.intended_use` | 10 | yes (phrasing miss) |
| `cop.training_content_summary` | 7 | yes (phrasing miss) |
| `xi.training_process` | 4 | yes (phrasing miss) |

Two distinct causes:
1. **Item-set mismatch (sufficient on its own to FAIL).** The verifier's
   `gpai-eu-v2` pack gate-counts **training compute** (Annex XI 2(d)) and **energy
   consumption** (Annex XI 2(e)); the holdout-authoring item spec lists ten items
   and includes **neither**. An independent author following that spec documents
   neither, so every clean card is flagged on `xi.compute` and `xi.energy` — 28/28
   each — regardless of wording.
2. **Residual phrasing brittleness.** Even for items the author did cover,
   genuinely independent natural wording still misses the v2 synonym set on a
   fraction of cards (downstream-integration, acceptable-use, io-modality,
   data-summary, intended-use, testing/training-process, training-content
   summary). The v2 broadening (D-18/D-20) reduced but did not eliminate this.

V6 0.750: two planted unsourced-claim cases phrased as natural sentences were not
parsed by the prose detector.

### Comparison with pre-registered predictions (`reports/phase2-fix-predictions.md`)

- **Verdict:** predicted PASS *if* clean cards cover distribution, else FAIL on
  clean FP. Measured: **FAIL**. The prediction identified the *category*
  (spec/pack mismatch driving clean FP) but **under-estimated its breadth** — it
  named only `cop.distribution`, whereas the decisive items were `xi.compute` and
  `xi.energy` (also absent from the authoring spec), plus broader phrasing misses.
  (`cop.distribution` itself did **not** flag any clean card here — the author
  covered distribution, as the spec now requires.) Honest miss: too optimistic on
  clean FP, for a wider reason than the one flagged.
- **D-23 addendum held:** V2 recall 1.000 and **no V2 clean false positive** —
  the reverted plain-MLP estimate matched the independent author's standard
  (plain) `gpt_neox` counts, exactly as the addendum predicted.
- **Recall predictions:** V1–V5, V7 within/above predicted ranges; V6 0.750 is
  at the low edge of the 0.80–0.95 band (slightly below).

### Reading

The fixes measurably improved **recall** over the original GATE 2 (V5 0.75→1.000,
V6 0.50→0.750, V7 0.875→1.000) and the V3 multi-level machinery generalises
cleanly. GATE 2 still **FAILS on clean FP**, now revealed as primarily a
**documentation-item-set mismatch** between the verifier pack and the holdout
authoring spec (compute/energy), compounded by residual keyword brittleness —
not a regression in the fixes. The original GATE 2 = FAIL in `reports/phase2.md`
is unchanged; this is a separate, second FAIL on an independent set.

### Errata to the GATE 2 re-gate section (appended; verdict unchanged — still FAIL)

Three corrections confirmed by the alignment-round audit (the FAIL verdict, the
recall table and clean-FP total stand):

1. **V6 miss mechanism.** The two missed V6 cases were *not* a prose-parse
   failure — the prose claims were parsed. The verifier treats any benchmark that
   also appears in a structured record (model-index / result-file) as "sourced"
   and therefore does **not compare values**, so a prose value that *contradicts*
   the structured value had no check form at all. (Fixed in the align round,
   Step 3.)
2. **`xii.downstream_integration` was NOT in the authoring brief.** The re-gate
   table labelled it "yes (phrasing miss)"; that is wrong — like compute/energy,
   downstream-integration was absent from the item spec, so its 21 clean trips are
   an item-set mismatch, not a phrasing miss.
3. **Clean FP is not explained by compute/energy alone.** Zero clean cards failed
   on compute/energy *only*; the item-set mismatch (compute, energy,
   downstream-integration — none in the brief) and genuine phrasing misses on
   in-spec items (testing_process, io_modality, acceptable_use, data_summary,
   intended_use, training_content_summary, training_process) each account for
   roughly half of the 170 clean V4 trips.
