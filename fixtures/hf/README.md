# HF adapter fixtures

Recorded-shape bundles consumed by `FixtureFetcher` (see
`src/releaseseal/snapshot/hf_adapter.py`). Each bundle is:

```json
{
  "info":  { "...": "GET /api/models/{repo}?revision={rev} body (sha, cardData, siblings)" },
  "tree":  [ "GET /api/models/{repo}/tree/{rev}?recursive=true entries (path, size, lfs.sha256)" ],
  "files": { "config.json": "<text>", "README.md": "<text>", "...": "small files only" }
}
```

Tests run entirely offline against these; the live `HttpFetcher`
(`hf_live.py`) is used only by the optional, non-default smoke step.

**Provenance (DECISIONS.md D-11, updated in Phase 2 — audit note 2):**

- `real-tiny-gpt2.json`, `real-bert-tiny.json` — **live-recorded** via the smoke
  path (`hf_live.HttpFetcher`) from small public repos (`hf-internal-testing/
  tiny-random-gpt2`, `prajjwal1/bert-tiny`); metadata + small files only, no
  weights. Tests parse them offline.
- `v8-undeclared.json` — a bundle whose `config.json` is the **real**
  `EleutherAI/pythia-70m` config (recorded) wrapped in a model that declares no
  `base_model`, to exercise the V8 signal against the seeded `known_bases`.
- `lineage-chain.json` — a **multi-repo** bundle (child → parent → grandparent)
  authored to the API schema to exercise recursive lineage resolution offline.
- `tiny-clean.json`, `tiny-doc-gaps.json` — authored to the API schema
  (Phase-1); kept for the adapter's parsing tests.

Live recording is metadata-only and runs only on the smoke path; the default
test run is entirely offline against these saved bundles.
