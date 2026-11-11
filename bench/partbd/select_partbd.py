#!/usr/bin/env python3
"""Part B-D selection — rule-pinned, then frozen (Phase-E2 Step 3).

Query the HF API for datasets sorted by downloads (descending), walk down the
list, and select 36 that satisfy ALL of:
  * public and NOT gated; not disabled;
  * at least one data file the ``hf_dataset`` adapter can inventory
    (a tree entry whose ext is one of .jsonl/.csv/.parquet/.txt/.json);
and TOGETHER fill the strata:
  * >= 6 primarily non-English or multilingual;
  * >= 4 exposing Croissant metadata;
  * >= 4 with > 1M rows (per datasets-server /size);
  * license families spread across permissive / copyleft / non_commercial /
    other_or_unknown.

Freeze the result as bench/partbd/datasets.json (partbd-datasets/1): {repo_id,
revision} pairs, revision = the HEAD sha at freeze time. Metadata-only, $0 spend;
gated datasets are excluded, never authenticated against. Run once, commit the
frozen list, then run the audit against it.

    PYTHONPATH=src python3 bench/partbd/select_partbd.py
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

_BASE = "https://huggingface.co"
_DS = "https://datasets-server.huggingface.co"
_UA = "releaseseal-build/0.1 (metadata-only)"
_DATA_EXTS = (".jsonl", ".csv", ".parquet", ".txt", ".json")

TARGET = 36
MIN_NON_ENGLISH = 6
MIN_CROISSANT = 4
MIN_LARGE = 4            # > 1M rows
LARGE_ROWS = 1_000_000
WALK_LIMIT = 400         # how many top datasets to probe at most

PERMISSIVE = {"apache-2.0", "mit", "bsd-3-clause", "bsd", "cc-by-4.0", "cc-by-3.0",
              "cc-by-2.0", "cc-by-2.5", "odc-by", "cc0-1.0", "cdla-permissive-2.0",
              "cdla-permissive-1.0", "mpl-2.0", "unlicense", "openrail", "artistic-2.0"}
COPYLEFT = {"gpl-3.0", "gpl-2.0", "gpl", "lgpl-3.0", "lgpl", "agpl-3.0", "cc-by-sa-4.0",
            "cc-by-sa-3.0", "odc-odbl", "odbl", "cc-by-sa", "cdla-sharing-1.0", "osl-3.0"}
NON_COMMERCIAL = {"cc-by-nc-4.0", "cc-by-nc-3.0", "cc-by-nc-sa-4.0", "cc-by-nc-sa-3.0",
                  "cc-by-nc-nd-4.0", "cc-by-nc", "cc-by-nd-4.0"}


def _get(url: str, timeout=30.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read().decode("utf-8")


def _get_json(url: str, timeout=30.0):
    return json.loads(_get(url, timeout))


def _license_family(lic):
    if not lic:
        return "other_or_unknown"
    lic = str(lic).strip().lower()
    if lic in PERMISSIVE:
        return "permissive"
    if lic in COPYLEFT:
        return "copyleft"
    if lic in NON_COMMERCIAL:
        return "non_commercial"
    return "other_or_unknown"


def _languages(card):
    lang = (card or {}).get("language")
    if isinstance(lang, str):
        return [lang]
    if isinstance(lang, list):
        return [x for x in lang if isinstance(x, str)]
    return []


def _is_non_english(card, tags):
    langs = _languages(card)
    if any(l.lower() not in ("en", "en-us", "en-gb") for l in langs) and langs:
        return True
    if len(langs) > 1:
        return True
    return any("multilingual" in str(t).lower() for t in (tags or []))


def _has_data_file(tree):
    for e in tree:
        p = e.get("path", "")
        if any(p.lower().endswith(ext) for ext in _DATA_EXTS):
            return True
    return False


def _num_rows(repo):
    try:
        size = _get_json(f"{_DS}/size?dataset={urllib.parse.quote(repo)}").get("size", {})
        total = (size.get("dataset") or {}).get("num_rows")
        if isinstance(total, int):
            return total
        return sum(s.get("num_rows", 0) or 0 for s in size.get("configs", []))
    except Exception:
        return None


def _exposes_croissant(repo):
    try:
        obj = _get_json(f"{_BASE}/api/datasets/{repo}/croissant")
        return isinstance(obj, dict) and bool(obj.get("distribution") or obj.get("recordSet") or obj.get("license"))
    except Exception:
        return False


def probe(repo_id):
    """Return an attributes dict for a base-passing candidate, else None."""
    try:
        info = _get_json(f"{_BASE}/api/datasets/{repo_id}")
    except Exception:
        return None
    if info.get("private") or info.get("disabled"):
        return None
    if info.get("gated") not in (False, None):   # 'auto'/'manual'/True -> gated
        return None
    sha = info.get("sha")
    if not sha:
        return None
    try:
        tree = _get_json(f"{_BASE}/api/datasets/{repo_id}/tree/{sha}?recursive=true")
    except Exception:
        return None
    if not _has_data_file(tree):
        return None
    card = info.get("cardData") or {}
    tags = info.get("tags") or []
    lic = card.get("license")
    if isinstance(lic, list):
        lic = lic[0] if lic else None
    return {
        "repo_id": repo_id,
        "revision": sha,
        "declared_license": lic,
        "license_family": _license_family(lic),
        "non_english": _is_non_english(card, tags),
        "num_rows": _num_rows(repo_id),
        "exposes_croissant": _exposes_croissant(repo_id),
    }


def main() -> int:
    print("walking HF datasets by downloads (desc)...")
    listing = _get_json(f"{_BASE}/api/datasets?sort=downloads&direction=-1&limit={WALK_LIMIT}")
    pool = []
    for i, d in enumerate(listing, 1):
        repo = d.get("id")
        if not repo:
            continue
        attrs = probe(repo)
        flag = ""
        if attrs:
            attrs["large"] = isinstance(attrs["num_rows"], int) and attrs["num_rows"] > LARGE_ROWS
            pool.append(attrs)
            flag = (f"OK fam={attrs['license_family']} ne={int(attrs['non_english'])} "
                    f"cro={int(attrs['exposes_croissant'])} rows={attrs['num_rows']}")
        print(f"[{i:03d}] {repo:52s} {flag or 'skip'}")
        # Stop once the pool is comfortably large enough to satisfy strata + TARGET.
        if len(pool) >= max(TARGET + 24, 60):
            ne = sum(1 for a in pool if a["non_english"])
            cro = sum(1 for a in pool if a["exposes_croissant"])
            lg = sum(1 for a in pool if a["large"])
            if ne >= MIN_NON_ENGLISH and cro >= MIN_CROISSANT and lg >= MIN_LARGE:
                break

    # Greedy strata-first selection from the pool (download order preserved).
    chosen, chosen_ids = [], set()

    def take(pred, need):
        for a in pool:
            if len(chosen) >= TARGET or need <= 0:
                break
            if a["repo_id"] in chosen_ids or not pred(a):
                continue
            chosen.append(a)
            chosen_ids.add(a["repo_id"])
            need -= 1

    take(lambda a: a["non_english"], MIN_NON_ENGLISH)
    take(lambda a: a["exposes_croissant"], MIN_CROISSANT)
    take(lambda a: a["large"], MIN_LARGE)
    # ensure each present license family is represented
    for fam in ("permissive", "copyleft", "non_commercial", "other_or_unknown"):
        take(lambda a, f=fam: a["license_family"] == f, 1)
    # fill remaining slots with earliest unselected
    take(lambda a: True, TARGET - len(chosen))

    chosen = chosen[:TARGET]
    frozen = {
        "schema_version": "partbd-datasets/1",
        "frozen_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "selection_rule": ("HF datasets sorted by downloads desc; public & not gated & not "
                           "disabled & >=1 inventoriable data file; strata: >=6 non-English/"
                           "multilingual, >=4 Croissant, >=4 >1M rows, license families spread."),
        "walk_limit": WALK_LIMIT,
        "count": len(chosen),
        "strata": {
            "non_english": sum(1 for a in chosen if a["non_english"]),
            "exposes_croissant": sum(1 for a in chosen if a["exposes_croissant"]),
            "large_gt_1M_rows": sum(1 for a in chosen if a["large"]),
            "license_families": {fam: sum(1 for a in chosen if a["license_family"] == fam)
                                 for fam in ("permissive", "copyleft", "non_commercial", "other_or_unknown")},
        },
        "datasets": [{"repo_id": a["repo_id"], "revision": a["revision"],
                      "declared_license": a["declared_license"],
                      "license_family": a["license_family"],
                      "non_english": a["non_english"], "exposes_croissant": a["exposes_croissant"],
                      "num_rows": a["num_rows"], "large": a["large"]} for a in chosen],
    }
    out = os.path.join(ROOT, "bench", "partbd", "datasets.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(frozen, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"\nselected {len(chosen)} datasets -> {out}")
    print("strata:", json.dumps(frozen["strata"]))
    if len(chosen) < TARGET:
        print(f"WARNING: only {len(chosen)} < {TARGET} selected; widen WALK_LIMIT.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
