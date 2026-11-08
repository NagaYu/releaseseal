# Phase 3 — entrance announcement (DRAFT — not posted)

Short announcement drafts for the Hugging Face dataset / Static Space entrance.
**Nothing here is posted.** Posting happens only after the owner confirms exact
title, body and target, in a separate run. Wording discipline: evidence, not
certification; no "passing/compliant" claims.

## Candidate targets (and recommendation)

- **A — HF Hub discussion / Community tab** on a relevant model-cards or
  governance space. Lowest friction, conversational.
- **B — A short dataset-card note + Static Space link**, surfaced via the
  `huggingface_hub` forum / a model-card-integrity thread.
- **C — A `huggingface_hub` GitHub discussion** referencing the audit.

**Recommended: B first** (the dataset + Static Space are the artifact; the note
points at measured numbers and the honest limitation), then A if there is
engagement. Avoid framing as a compliance tool.

## Draft note (B)

> **ReleaseSeal: an offline, deterministic check of model-card documentation vs. a
> release's artifacts — with re-verifiable evidence packs.**
>
> I audited 40 popular public models (pinned revisions, metadata only) for the
> presence of EU AI Act Annex XI/XII documentation items. Per item, missing in:
> copyright policy 40/40, public training-content summary 38/40, training compute
> 34/40, energy consumption 33/40, testing process 30/40, distribution 26/40,
> acceptable-use 21/40, downstream-integration 19/40 (full table + per-model
> evidence in the dataset/Space). 2 of the 40 are gated, so their config was not
> fetchable and their inspection was card-metadata only. Each finding ships as a
> hash-chained evidence pack you can re-verify offline.
>
> **Honest limitation:** the documentation-presence check (V4) is a pattern-based
> *screening* signal — on a sealed, independently-written test set of fully
> documented cards it over-fired (82% clean false-positive rate), so a V4 finding
> means "a place to check," not "a confirmed omission." The artifact checks
> (hashes, config facts, license lineage, loadability — V1–V3, V5–V7) are a
> different, far lower-false-positive character, and recall on all seven classes
> was 1.000 on the final sealed set (earlier sets scored lower on some classes:
> v1 — V5 0.750, V6 0.500, V7 0.875; v2 — V6 0.750).
>
> It is **evidence, not certification** — it does not attest compliance. Code,
> synthetic bench, rule packs and the full gate history (including the failures)
> are published. Feedback on the documentation-presence signal especially welcome.

## Draft note (A) — shorter

> Built a small offline verifier that cross-checks a model card's claims against
> its config/hashes/license lineage and emits re-verifiable evidence packs. Ran it
> over 40 popular models for EU AI Act Annex XI/XII documentation presence (e.g.
> copyright policy missing 40/40, training-content summary 38/40; 2 gated models
> were inspected on card metadata only, config unfetchable). The presence check is
> a screening signal (over-fires on well-written cards — 82% clean FP on a sealed
> set), so treat V4 as "check here", not a verdict. Evidence, not certification.
> Numbers, code and the honest gate history are linked.

## Pre-post checklist (for the owner's confirmation run)

- [ ] Exact title / body / target confirmed by owner
- [ ] No "passing" / "compliant" / "certified" wording
- [ ] Per-item numbers (no bare overall rate); gated-2 disclosure present
- [ ] V4 limitation (82% clean FP) stated
- [ ] Links resolve (dataset, Space); holdout cases not referenced/exposed
