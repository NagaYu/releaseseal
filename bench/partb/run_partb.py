#!/usr/bin/env python3
"""Part B runner — audit the frozen real-release list (design §5, SPEC.md).

Fetches each model's snapshot from the HF Hub API at its PINNED revision
(metadata + small files only; NO weight bytes), verifies it with the frozen
rule packs, writes an evidence pack + snapshot per model under audit/partb/, and
emits audit/partb/summary.json. Smoke-path only (uses the network); never run by
the test suite.

Usage:
    PYTHONPATH=src python3 bench/partb/run_partb.py \
        --models bench/partb/models.json --out audit/partb
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from releaseseal.evidence import build_pack  # noqa: E402
from releaseseal.rules import load_packs, pack_versions  # noqa: E402
from releaseseal.snapshot.hf_adapter import build_snapshot  # noqa: E402
from releaseseal.snapshot.hf_live import HttpFetcher  # noqa: E402
from releaseseal.verify import Context, gate_counted, verify  # noqa: E402

CLASSES = ("V1", "V2", "V3", "V4", "V5", "V6", "V7")


class CachingFetcher:
    """Wraps HttpFetcher with per-run memoisation so shared ancestors are
    fetched once across the whole Part B set."""

    def __init__(self):
        self._f = HttpFetcher()
        self._mi, self._tr, self._ft = {}, {}, {}

    def model_info(self, repo, rev):
        k = (repo, rev)
        if k not in self._mi:
            self._mi[k] = self._f.model_info(repo, rev)
        return self._mi[k]

    def tree(self, repo, rev):
        k = (repo, rev)
        if k not in self._tr:
            self._tr[k] = self._f.tree(repo, rev)
        return self._tr[k]

    def file_text(self, repo, rev, path):
        k = (repo, rev, path)
        if k not in self._ft:
            self._ft[k] = self._f.file_text(repo, rev, path)
        return self._ft[k]


def _safe(repo: str) -> str:
    return repo.replace("/", "__")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=os.path.join(ROOT, "bench/partb/models.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "audit/partb"))
    args = ap.parse_args()

    with open(args.models, encoding="utf-8") as fh:
        frozen = json.load(fh)
    os.makedirs(args.out, exist_ok=True)
    packs = load_packs()
    ctx = Context(packs=packs)
    captured_at = datetime.date.today().isoformat()
    fetcher = CachingFetcher()

    rows = []
    for i, m in enumerate(frozen["models"], 1):
        repo, rev = m["repo_id"], m["revision"]
        rec = {"repo_id": repo, "revision": rev, "declared_license": m.get("declared_license"),
               "gated": m.get("gated"), "error": None, "by_class": {c: 0 for c in CLASSES},
               "codes": {}, "n_findings": 0, "n_heuristic": 0, "config_present": None}
        try:
            snap = build_snapshot(repo, rev, fetcher, captured_at=captured_at)
            doc = verify(snap, ctx=ctx)
            counted = gate_counted(doc["findings"])
            rec["config_present"] = snap.get("config") is not None
            rec["n_findings"] = len(counted)
            rec["n_heuristic"] = sum(1 for f in doc["findings"] if f.get("heuristic"))
            for f in counted:
                rec["by_class"][f["check"]] += 1
                rec["codes"][f["code"]] = rec["codes"].get(f["code"], 0) + 1
            pack = build_pack(snap, doc)
            with open(os.path.join(args.out, f"{_safe(repo)}.snap.json"), "w", encoding="utf-8") as fh:
                json.dump(snap, fh, ensure_ascii=False)
            with open(os.path.join(args.out, f"{_safe(repo)}.pack.json"), "w", encoding="utf-8") as fh:
                json.dump(pack, fh, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            rec["error"] = f"{type(e).__name__}: {e}"
        rows.append(rec)
        print(f"[{i:02d}/{len(frozen['models'])}] {repo:48s} "
              f"{'ERR '+rec['error'] if rec['error'] else 'findings='+str(rec['n_findings'])+' '+str({c:n for c,n in rec['by_class'].items() if n})}")

    ok = [r for r in rows if not r["error"]]
    occ = {c: sum(1 for r in ok if r["by_class"][c] > 0) for c in CLASSES}
    occ_rate = {c: (occ[c] / len(ok) if ok else 0.0) for c in CLASSES}
    all_codes = {}
    for r in ok:
        for code, n in r["codes"].items():
            all_codes[code] = all_codes.get(code, 0) + n
    summary = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "captured_at": captured_at,
        "rule_packs": pack_versions(packs),
        "n_models": len(rows),
        "n_ok": len(ok),
        "n_error": len(rows) - len(ok),
        "occurrence_count": occ,
        "occurrence_rate": occ_rate,
        "code_totals": dict(sorted(all_codes.items(), key=lambda kv: -kv[1])),
        "zero_finding_models": [r["repo_id"] for r in ok if r["n_findings"] == 0],
        "models": rows,
    }
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("\nOccurrence rate (V1-V7):", {c: round(occ_rate[c], 3) for c in CLASSES})
    print("errors:", summary["n_error"], "| zero-finding:", len(summary["zero_finding_models"]))
    print("wrote", os.path.join(args.out, "summary.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
