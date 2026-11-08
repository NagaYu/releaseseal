"""Bench scorer: per-class recall + clean false-positive rate (SPEC.md §6.3).

Deterministic. V8 (heuristic) findings are ignored entirely.
"""
from __future__ import annotations

from typing import Optional

from ..verify import Context, gate_counted, verify

CLASSES = ("V1", "V2", "V3", "V4", "V5", "V6", "V7")


def score(manifest: dict, *, ctx: Optional[Context] = None) -> dict:
    if ctx is None:
        ctx = Context.default()

    per_class_total = {c: 0 for c in CLASSES}
    per_class_hit = {c: 0 for c in CLASSES}
    clean_total = 0
    clean_fp = 0
    details = []

    for case in manifest.get("cases", []):
        snap = case["snapshot"]
        findings = gate_counted(verify(snap, ctx=ctx)["findings"])
        fired = {f["check"] for f in findings}
        expected = set(case.get("expected", []))

        if case["kind"] == "clean":
            clean_total += 1
            if fired:
                clean_fp += 1
                details.append({"id": case["id"], "kind": "clean", "unexpected": sorted(fired)})
        else:
            for c in expected:
                if c in CLASSES:
                    per_class_total[c] += 1
                    if c in fired:
                        per_class_hit[c] += 1
                    else:
                        details.append({"id": case["id"], "kind": case["kind"],
                                        "missed": c, "fired": sorted(fired)})

    recall = {
        c: (per_class_hit[c] / per_class_total[c] if per_class_total[c] else None)
        for c in CLASSES
    }
    clean_fp_rate = (clean_fp / clean_total) if clean_total else 0.0
    out = {
        "recall": recall,
        "per_class_total": per_class_total,
        "per_class_hit": per_class_hit,
        "clean_total": clean_total,
        "clean_fp": clean_fp,
        "clean_fp_rate": clean_fp_rate,
        "details": details,
    }
    walk = lineage_walk_accuracy(manifest, ctx=ctx)
    if walk is not None:
        out["lineage_walk"] = walk
    return out


# V3 codes that represent a genuine lineage violation (license_unknown is not one).
_VIOLATION_CODES = {"license_incompatible", "attribution_missing"}


def lineage_walk_accuracy(manifest: dict, *, ctx=None):
    """design §5 metric: fraction of lineage cases whose *detected* violating-
    ancestor set equals the planted ``lineage_truth`` set. Returns None if the
    manifest carries no lineage_truth (e.g. the plain dev split).
    """
    if ctx is None:
        ctx = Context.default()
    cases = [c for c in manifest.get("cases", []) if "lineage_truth" in c]
    if not cases:
        return None
    correct = 0
    mismatches = []
    for case in cases:
        findings = verify(case["snapshot"], ctx=ctx)["findings"]
        detected = {f.get("subject") for f in findings
                    if f["check"] == "V3" and f["code"] in _VIOLATION_CODES and f.get("subject")}
        truth = set(case.get("lineage_truth") or [])
        if detected == truth:
            correct += 1
        else:
            mismatches.append({"id": case["id"], "truth": sorted(truth), "detected": sorted(detected)})
    return {"total": len(cases), "correct": correct,
            "accuracy": correct / len(cases), "mismatches": mismatches}


def gate1(scored: dict, *, recall_floor: float = 0.90, fp_ceiling: float = 0.05) -> dict:
    recalls = scored["recall"]
    recall_ok = all((r is not None and r >= recall_floor) for r in recalls.values())
    fp_ok = scored["clean_fp_rate"] <= fp_ceiling
    return {
        "pass": bool(recall_ok and fp_ok),
        "recall_ok": recall_ok,
        "fp_ok": fp_ok,
        "recall_floor": recall_floor,
        "fp_ceiling": fp_ceiling,
    }
