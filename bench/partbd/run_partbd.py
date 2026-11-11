#!/usr/bin/env python3
"""Part B-D audit runner — audit the frozen real-dataset list (Phase-E2 Step 3).

For each frozen {repo_id, revision}: build a dsnapshot with the hf_dataset
adapter (metadata + a dsample/1-capped content sample via the datasets-server
rows endpoint), verify it with the dataset packs, write an evidence pack, and
emit audit/partbd/summary.json (partbd-summary/1). Metadata + capped samples
only; NO bulk downloads; $0 spend; gated datasets excluded upstream (selection).

Privacy (D-31/D-40): the on-disk snapshot file OMITS the raw sample row text
(third-party content / possible PII is never persisted); the evidence pack's W4
findings are masked by the check. The true snapshot hash is recorded. One dataset
never aborts the run; unsupported/script datasets record an empty sample + note.

    PYTHONPATH=src python3 bench/partbd/run_partbd.py \
        --datasets bench/partbd/datasets.json --out audit/partbd
"""
from __future__ import annotations

import argparse
import copy
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from releaseseal.evidence import build_pack  # noqa: E402
from releaseseal.rules import load_packs, pack_versions  # noqa: E402
from releaseseal.snapshot.hf_dataset import build_dataset_snapshot  # noqa: E402
from releaseseal.snapshot.hf_live import DatasetHttpFetcher  # noqa: E402
from releaseseal.verify import DATASET_PACK_IDS, gate_counted_dataset, verify_dataset  # noqa: E402

CLASSES = ("W1", "W2", "W3", "W4", "W5", "W6", "W7")

# Finding codes that represent a violated real declaration vs. a measurement.
CLAIM_VIOLATION_CODES = {
    "license_inconsistent", "source_license_incompatible", "declared_file_missing",
    "undeclared_data_file", "row_count_mismatch", "pii_claim_falsified",
    "decontamination_claim_falsified", "dedup_rate_mismatch", "language_share_mismatch",
    "declared_language_absent", "undeclared_language_dominant",
}
MEASUREMENT_CODES = {"contamination_measured", "dedup_measured", "pii_detected", "card_field_missing"}


def _safe(repo: str) -> str:
    return repo.replace("/", "__")


def _coverage(snap):
    per = (snap.get("sample") or {}).get("per_split") or []
    rows_sampled = sum(p.get("rows_sampled", 0) or 0 for p in per)
    splits = {s.get("name"): s.get("num_rows") for s in (snap.get("splits") or [])}
    rows_total = sum(v for v in splits.values() if isinstance(v, int))
    return {"rows_sampled": rows_sampled,
            "rows_total": rows_total if rows_total else None,
            "splits_sampled": [p.get("split") for p in per],
            "n_splits_total": len(splits)}


def _redacted_snapshot(snap):
    """Snapshot copy safe to persist: raw sample row text removed."""
    d = copy.deepcopy(snap)
    samp = d.get("sample") or {}
    n = len(samp.get("rows") or [])
    samp["rows"] = []
    samp["rows_omitted_for_privacy"] = n
    d["content_redacted_for_privacy"] = True
    d["redaction_note"] = ("sample row text omitted on disk — raw third-party content / "
                           "possible PII is never persisted (D-31/D-40); snapshot_sha256 is "
                           "the hash of the full verified snapshot")
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default=os.path.join(ROOT, "bench/partbd/datasets.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "audit/partbd"))
    args = ap.parse_args()

    with open(args.datasets, encoding="utf-8") as fh:
        frozen = json.load(fh)
    os.makedirs(args.out, exist_ok=True)
    packs = load_packs(DATASET_PACK_IDS)
    captured_at = datetime.date.today().isoformat()
    fetcher = DatasetHttpFetcher()

    rows = []
    datasets = frozen["datasets"]
    for i, m in enumerate(datasets, 1):
        repo, rev = m["repo_id"], m["revision"]
        rec = {"repo_id": repo, "revision": rev,
               "declared_license": m.get("declared_license"),
               "license_family": m.get("license_family"),
               "non_english": m.get("non_english"), "exposes_croissant": m.get("exposes_croissant"),
               "num_rows": m.get("num_rows"), "large": m.get("large"),
               "error": None, "coverage": None,
               "by_class": {c: 0 for c in CLASSES}, "codes": {},
               "n_counted": 0, "n_info": 0, "n_heuristic": 0,
               "claim_violations": 0, "measurements": 0,
               "w4_detectors": {}, "w5_overlap": {}, "w6_dedup": None,
               "w7_problems": [], "w1_inconsistent": False, "w1_unknown": False}
        try:
            snap = build_dataset_snapshot(repo, rev, fetcher, captured_at=captured_at)
            doc = verify_dataset(snap, pack_ids=DATASET_PACK_IDS)
            findings = doc["findings"]
            counted = gate_counted_dataset(findings)
            rec["coverage"] = _coverage(snap)
            rec["n_counted"] = len(counted)
            rec["n_info"] = sum(1 for f in findings if f.get("severity") == "info")
            rec["n_heuristic"] = sum(1 for f in findings if f.get("heuristic"))
            for f in counted:
                rec["by_class"][f["check"]] += 1
            for f in findings:
                code = f["code"]
                rec["codes"][code] = rec["codes"].get(code, 0) + 1
                if code in CLAIM_VIOLATION_CODES:
                    rec["claim_violations"] += 1
                elif code in MEASUREMENT_CODES:
                    rec["measurements"] += 1
                if code in ("pii_detected", "pii_claim_falsified"):
                    det = (f.get("evidence") or {}).get("actual", "")
                    did = det.split("(")[-1].rstrip(")") if "(" in det else "?"
                    rec["w4_detectors"][did] = rec["w4_detectors"].get(did, 0) + 1
                if code in ("contamination_measured", "decontamination_claim_falsified"):
                    sid = f.get("subject") or "?"
                    rec["w5_overlap"][sid] = (f.get("evidence") or {}).get("actual")
                if code == "dedup_measured" or code == "dedup_rate_mismatch":
                    rec["w6_dedup"] = (f.get("evidence") or {}).get("actual")
                if code in ("declared_language_absent", "undeclared_language_dominant",
                            "language_share_mismatch"):
                    rec["w7_problems"].append(f.get("subject"))
                if code == "license_inconsistent":
                    rec["w1_inconsistent"] = True
                if code == "license_unknown" and f["check"] == "W1":
                    rec["w1_unknown"] = True
            pack = build_pack(snap, doc)
            with open(os.path.join(args.out, f"{_safe(repo)}.snap.json"), "w", encoding="utf-8") as fh:
                json.dump(_redacted_snapshot(snap), fh, ensure_ascii=False)
            with open(os.path.join(args.out, f"{_safe(repo)}.pack.json"), "w", encoding="utf-8") as fh:
                json.dump(pack, fh, ensure_ascii=False)
        except Exception as e:  # noqa: BLE001
            rec["error"] = f"{type(e).__name__}: {e}"
        rows.append(rec)
        cov = rec["coverage"] or {}
        print(f"[{i:02d}/{len(datasets)}] {repo:50s} "
              + (f"ERR {rec['error']}" if rec["error"]
                 else f"counted={rec['n_counted']} cov={cov.get('rows_sampled')}/{cov.get('rows_total')} "
                      f"{ {c:n for c,n in rec['by_class'].items() if n} }"))

    ok = [r for r in rows if not r["error"]]
    n = len(ok)

    def frac(pred):
        return (sum(1 for r in ok if pred(r)) / n) if n else 0.0

    # Step 0 Part B-D predictions, scored hit/miss against this audit.
    predictions = [
        {"id": "P1_any_counted", "statement": ">=60% of datasets yield >=1 counted finding",
         "threshold": 0.60, "measured": frac(lambda r: r["n_counted"] >= 1)},
        {"id": "P2_w1_inconsistency", "statement": "W1 license inconsistency in >=25% of datasets",
         "threshold": 0.25, "measured": frac(lambda r: r["w1_inconsistent"])},
        {"id": "P3_w4_detector_hits", "statement": "W4 detector hits in >=15% of datasets",
         "threshold": 0.15, "measured": frac(lambda r: bool(r["w4_detectors"]))},
        {"id": "P4_w5_overlap", "statement": "W5 measured overlap > 0 in >=10% of datasets",
         "threshold": 0.10, "measured": frac(lambda r: any(
             (v is not None and float(v) > 0) for v in r["w5_overlap"].values()))},
        {"id": "P5_w7_language", "statement": "W7 declared-language problems in >=10% of datasets",
         "threshold": 0.10, "measured": frac(lambda r: bool(r["w7_problems"]))},
        {"id": "P6_w8_completeness", "statement": "W8 completeness gaps in >=50% (signal only)",
         "threshold": 0.50, "measured": frac(lambda r: r["codes"].get("card_field_missing", 0) > 0)},
    ]
    for p in predictions:
        p["hit"] = p["measured"] >= p["threshold"]

    code_totals = {}
    for r in ok:
        for code, c in r["codes"].items():
            code_totals[code] = code_totals.get(code, 0) + c
    by_class_occ = {c: sum(1 for r in ok if r["by_class"][c] > 0) for c in CLASSES}

    summary = {
        "schema_version": "partbd-summary/1",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "captured_at": captured_at,
        "rule_packs": pack_versions(packs),
        "sample_params": {"rule": "dsample/1", "rows_per_split": fetcher.rows_per_split,
                          "max_splits": fetcher.max_splits},
        "n_datasets": len(rows), "n_ok": n, "n_error": len(rows) - n,
        "counted_finding_rate_by_class": {c: (by_class_occ[c] / n if n else 0.0) for c in CLASSES},
        "counted_finding_occurrence_by_class": by_class_occ,
        "datasets_with_any_counted": sum(1 for r in ok if r["n_counted"] >= 1),
        "strata_totals": {
            "claim_violations": sum(r["claim_violations"] for r in ok),
            "measurements": sum(r["measurements"] for r in ok),
            "w1_license_unknown_datasets": sum(1 for r in ok if r["w1_unknown"]),
        },
        "code_totals": dict(sorted(code_totals.items(), key=lambda kv: -kv[1])),
        "predictions": predictions,
        "datasets": rows,
    }
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("\n== predictions ==")
    for p in predictions:
        print(f"  {'HIT ' if p['hit'] else 'MISS'} {p['id']:20s} measured={p['measured']:.3f} thr={p['threshold']}")
    print(f"ok={n} err={len(rows)-n} any-counted={summary['datasets_with_any_counted']}/{n}")
    print("wrote", os.path.join(args.out, "summary.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
