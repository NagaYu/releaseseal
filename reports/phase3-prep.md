# Phase 3 — publication prep (prep only; nothing pushed or posted)

This round prepared the public artifacts. **No push, no HF upload, no Space
creation, no issue/post.** Publication executes only after the owner's final
confirmation, in a separate run. The verifier code and rule packs are unchanged
(frozen at `73eef79`); test expectations unchanged.

## Export structure (`~/Desktop/Claude code/ReleaseSeal-public/`)

A new repository, to be initialised with a **single clean commit** authored by the
noreply address. Contents:

- `src/releaseseal/` — frozen verifier + rule packs (`gpai-eu-v1`/`v2`/`v3`,
  `hub-metadata-v1`, `license-terms-v1`, `fingerprints-v1`).
- `tests/` — offline suite (passes self-contained: no holdout/audit dependency).
- `bench/partb/` — frozen model list + runner (for reproducibility).
- `fixtures/hf/` — recorded public-model API bundles (offline tests).
- `docs/` — `bom-mapping.md`, `authoring-item-set.md` (the 16-item single source).
- `reports/` — phase1, phase2, phase2-fix, phase2-align, partb, partb-v2,
  partb-v3, the three pre-registered prediction files, this file, and the
  entrance draft.
- `SPEC.md`, `DECISIONS.md`, `STATUS.md`, `pyproject.toml`, `.gitignore`.
- `README.md` (English lead), `LICENSE` (All Rights Reserved + transfer).
- `hf-dataset-card.md`, `hf-dataset/` (dev + dev_ext manifests), `hf-audit/`
  (Part B v3 tables + representative evidence packs), `hf-space/` (static page).

**Excluded (verified absent):** all holdout case data (v1/v2/v3 and the retired
holdout-2 are in sibling folders, never in this repo); `audit/` raw data (the
aggregates are already summarised in the reports); the internal design doc; any
non-noreply history (the export is a fresh single-commit history).

## README disclosure checklist (self-check)

- [x] §2 Part B headline reported **per item** (copyright 40/40, training-content
      summary 38/40, compute 34/40, energy 33/40, …) — **no bare overall rate**;
      gated-2 disclosure included.
- [x] §5 Gate history table is honest: GATE 1 PASS; GATE 2 FAIL (v1 fixed-phrase
      brittleness); re-gate FAIL (v2 item-set + phrasing); final re-gate FAIL (v3
      phrasing only, clean FP 82%, recall V1–V7 all 1.000); stop rule → published
      as-is.
- [x] §6 Known limitation — V4 is a screening signal; clean FP 82% with per-item
      decomposition; "read as a place to check"; contrast with V1–V3/V5–V7
      artifact checks.
- [x] Wording discipline throughout: **evidence, not certification**; no
      passing/compliance guarantees.
- [x] Holdout cases never included; only aggregates.

## HF materials status (prepared, NOT uploaded)

- `hf-dataset/` — `dev-manifest.json` (120), `dev_ext-manifest.json` (24),
  dataset card (`README.md`). Holdout-not-published stated.
- `hf-audit/` — `partb-v3-results.md` (per-item + per-model tables, gated
  disclosure) and three representative hash-chained evidence packs in `packs/`.
- `hf-space/` — self-contained static `index.html` (no Gradio/dynamic hosting):
  precomputed Part B table, a representative-evidence-pack viewer, gate history,
  and the non-certification disclaimer.

## Remaining publication-execution steps (owner final confirmation required)

1. **Review** the export, README, and HF drafts; confirm exact public text.
2. **Initialise & push** the public GitHub repo (noreply author) — *not done*.
3. **Upload** `hf-dataset/` as a HF dataset and `hf-audit/` alongside it — *not done*.
4. **Create** the HF **Static** Space from `hf-space/` — *not done*.
5. **Post** the entrance note (target/body per `reports/phase3-entrance-draft.md`,
   owner-confirmed exact wording) — *not done*.

None of 2–5 is performed in this prep round.
