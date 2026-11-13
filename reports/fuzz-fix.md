# ReleaseSeal — fuzz-findings fix (F-1 … F-5)

Fix session for the five defects found by the adversarial fuzz audit
(`reports/fuzz-audit.md`, branch `fuzz-audit` tip `dc368cb`). Branch
`fix-fuzz-f1-f5`, cut from `dc368cb`; local commit only, nothing pushed, the
sealed holdouts never opened, `fuzz/` run but never edited. The pinned fix
semantics were implemented as given; no semantics were redesigned.

## Files changed and why

| File | Finding | Change |
|---|---|---|
| `src/releaseseal/bom/verify_bom.py` | F-1 | Import the shared `_norm_alg` from `facts`; the hash comparator now compares iff `_norm_alg(alg) == "SHA-256"` instead of `alg.upper().replace("-","") == "SHA256"`. One canonicalization for both importers; whitespace/underscore labels now decide. |
| `src/releaseseal/cli.py` | F-2 | New `CliError`; `_load_json` maps `JSONDecodeError`/`UnicodeDecodeError`/`OSError` to `CliError`; `main` renders any `CliError` as `error: …` on stderr with exit 2. Applies to every `_load_json` subcommand. |
| `src/releaseseal/snapshot/cardparse.py` | F-3/F-4/F-5 | Parser internals rewritten as a small recursive-descent `_YamlParser` with an anchor registry: flow lists-of-maps parse recursively (types preserved), anchors/aliases/merge keys resolve, inline `#` comments strip quote-/boundary-aware, double-quoted escapes and single-quoted `''` process. |
| `tests/test_fuzz_fix_f1_bom_alg.py` | F-1 | 21 regression cases (see below). |
| `tests/test_fuzz_fix_f2_cli_loader.py` | F-2 | 19 regression cases. |
| `tests/test_fuzz_fix_f345_cardparse.py` | F-3/4/5 | 11 regression cases. |
| `DECISIONS.md` | — | D-46, D-47, D-48 appended. |
| `reports/fuzz-fix.md` | — | This report. |

No change touches `bench/`, the rule packs (`src/releaseseal/rules/`), `fixtures/`,
`fuzz/`, or the model-side `src/releaseseal/verify/` tree.

## DECISIONS entries (full text appended to `DECISIONS.md`)

- **D-46 — one SHA-256 alg canonicalization for both importers at verify
  (completes D-44).** The verify-side comparator canonicalizes the label through
  the single shared `_norm_alg` rule (`verify_bom` imports it from `facts`): a hash
  compares iff `_norm_alg(alg) == "SHA-256"`, so the same label yields the same
  verdict in CycloneDX and SPDX — a differing value fires `bom_hash_mismatch`, an
  equal value is compared-clean (not `unverifiable`) — while a label canonicalizing
  to no known algorithm stays `unverifiable`. Fixed at verify, so the facts shape
  and BOM export round-trip are unchanged.
- **D-47 — CLI file-load error contract: `error:` + exit 2, never a traceback.**
  `_load_json` catches `JSONDecodeError`/`UnicodeDecodeError`/`OSError` and
  re-raises `CliError`; `main` renders it. `CliError` is not a `ValueError`, so a
  subcommand's own `except ValueError` never swallows a file-load failure; the
  contract holds for every `_load_json` subcommand. Encoding stays `utf-8` so a
  UTF-8-BOM/UTF-16 file errors rather than being silently accepted.
- **D-48 — cardparse subset extension + the never-silent rule.** Flow
  lists-of-maps parse recursively (scalar types preserved); anchors/aliases/merge
  keys resolve through a per-parse registry (explicit keys win over `<<`); inline
  `#` comments strip quote-/boundary-aware (glued `a#b` stays content); double- and
  single-quoted escapes process. The never-silent rule: no declaration-bearing
  construct is silently dropped or corrupted per field — anything still
  unrepresentable takes the whole-document `{}` + note fallback. `hf` and the bench
  generators don't use `cardparse`, so no gate number moves.

## Verification

### 1. Test suite

```
python -m pytest -q   →   234 passed   (baseline 183 + 51 new)
```

New regression tests (per the report's minimal repros):

- **F-1 (21):** the four alg labels `SHA-256` / `" SHA-256"` / `"SHA-256 "` /
  `"SHA_256"` × match and mismatch on CycloneDX; SPDX parity (match + mismatch) for
  each; and five genuinely-unknown algs that must stay `unverifiable`.
- **F-2 (19):** the seven trigger shapes + a missing file through the real CLI
  (`rc==2`, `error:`, no traceback); the triggers at the `_load_json` loader level
  (`CliError`); and the contract applied to a second subcommand (`verify`).
- **F-3/4/5 (11):** block ≡ flow extraction for `sources` and `file_inventory`
  (rows stays int); anchored scalar, anchored number + alias reuse in a second
  field, merge key, merge-with-explicit-key-wins; inline comment, a glued `a#b`
  control that stays content, a double-quoted escape, a single-quoted `''`.

### 2. Dev-d re-score — identical to the published table

```
dev-d cases_sha256 : 0e2633a26ed15c72b585e00697c4b1f013d212a0630e214f0c9a33bc21a4ab32   (unchanged anchor)
per-class recall   : W1 1.000  W2 1.000  W3 1.000  W4 1.000  W5 1.000  W6 1.000  W7 1.000
clean FP           : 0 / 36
GATE E1            : PASS
```

Bench files untouched (`git diff dc368cb -- bench` is empty).

### 3. BOM mini-bench re-score

```
BOM mini-bench : 24 / 24   (exact match)
```

### 4. Fuzz campaign (`python fuzz/run.py`, `fuzz/` unmodified, seed 20261119)

Before (committed `fuzz/results/campaign.json` at `dc368cb`) → after (this fix):

| target | crash | wrong_verdict | wrong_parse | clean |
|---|---:|---:|---:|---:|
| bom_importer (before) | **7** | **8** | — | 4246 |
| bom_importer (after)  | **0** | **0** | — | 4261 |
| snapshot_parser (before) | 0 | — | **45** | 199 |
| snapshot_parser (after)  | 0 | — | **0** | 244 |

| target | attempted | caught | by_design | evasion |
|---|---:|---:|---:|---:|
| w_check_evasion (before) | 242 | 240 | 2 | 0 |
| w_check_evasion (after)  | 242 | 240 | 2 | 0 |

W-check end-to-end README leg:

| | block_caught | flow_caught | flow_parser_miss |
|---|---:|---:|---:|
| before | 84 | 60 | **24** |
| after  | 84 | **84** | **0** |

All required bars met: BOM crashes 0, BOM wrong-verdicts 0; W-check line identical
(240 caught / 2 by-design / 0 evasions); snapshot wrong-parse 0; end-to-end
`flow_parser_miss` 0 (block 84, flow 84). (`fuzz/results/campaign.json` is restored
to its `dc368cb` content after the run, so `fuzz/` carries no fix-session diff.)

### 5. F-2 CLI evidence (each trigger + a missing file, through the real CLI)

| input | exit code | stderr starts `error:` | no traceback |
|---|---:|---|---|
| `truncated-open-array` | 2 | yes | yes |
| `truncated-mid` | 2 | yes | yes |
| `empty-file` | 2 | yes | yes |
| `not-json` | 2 | yes | yes |
| `trailing-garbage` | 2 | yes | yes |
| `lonely-brace` | 2 | yes | yes |
| `utf16` | 2 | yes | yes |
| `missing-file` | 2 | yes | yes |

### 6. Diff scope

`git diff dc368cb --stat` (the fix, relative to the audit baseline):

```
 src/releaseseal/bom/verify_bom.py     |  11 +-
 src/releaseseal/cli.py                |  33 +++-
 src/releaseseal/snapshot/cardparse.py | 316 +++++++++++++++++++++++-----------
 tests/test_fuzz_fix_f1_bom_alg.py     |  (new)
 tests/test_fuzz_fix_f2_cli_loader.py  |  (new)
 tests/test_fuzz_fix_f345_cardparse.py |  (new)
 DECISIONS.md                          |  (appended)
 reports/fuzz-fix.md                   |  (new)
```

`git diff dc368cb --stat -- bench fuzz fixtures src/releaseseal/rules src/releaseseal/verify`
is **empty**. (Against `5879ba9`, the diff additionally shows the audit branch's own
`fuzz/` tree and `reports/fuzz-audit.md`, which are `dc368cb`'s additions, not this
fix's; the fix changes nothing under `fuzz/`.)

## Self-judgement per finding

- **F-1 — fixed.** Sloppy SHA-256 labels (`" SHA-256"`, `"SHA-256 "`, `"SHA_256"`)
  now fire `bom_hash_mismatch` on a differing hash and compare clean on a matching
  one, in both CycloneDX and SPDX; unknown algs stay `unverifiable`. Fuzz
  wrong-verdicts 8 → 0; 21 regression tests green.
- **F-2 — fixed.** All seven triggers + a missing file produce `error:` + exit 2
  with no traceback, through the real CLI and at the loader level, for every
  `_load_json` subcommand. Fuzz BOM crashes 7 → 0; 19 regression tests green.
- **F-3 — fixed.** Flow lists-of-maps parse identically to block style (types
  preserved); planted W2/W3 violations re-encoded as flow README YAML are now caught
  end-to-end. Fuzz `flow_parser_miss` 24 → 0 (flow 84/84); block ≡ flow tests green.
- **F-4 — fixed.** Anchored scalars/numbers, aliases, and `<<` merge keys resolve
  (explicit keys win); no spurious `license_unknown` and no dropped `dedup_rate`/
  `pii`. Covered by the snapshot wrong-parse 45 → 0 result and 4 regression tests.
- **F-5 — fixed.** Inline `#` comments strip (glued `a#b` kept as content), and
  double-/single-quoted escapes process. Covered by the snapshot wrong-parse 45 → 0
  result and 3 regression tests.

The never-silent rule holds: the fuzz program-3 construct set reaches wrong-parse 0,
and any construct the subset still cannot represent takes the whole-document `{}`
fallback rather than a per-field drop.
