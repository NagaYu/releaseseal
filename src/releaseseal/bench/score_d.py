"""Bench Part A-D scorer: per-class recall + clean FP rate (SPEC.md §E1.7/§6.3).

Deterministic. The counting rule (§E1.3, D-31): recall/FP count only findings
with ``heuristic == false`` AND ``severity != "info"`` — so W8, and the
``contamination_measured`` / ``dedup_measured`` info findings, never count.
"""
from __future__ import annotations

from typing import Optional

from ..verify import Context, gate_counted_dataset, verify_dataset
from ..verify.wchecks import DATASET_PACK_IDS

CLASSES = ("W1", "W2", "W3", "W4", "W5", "W6", "W7")


def score(manifest: dict, *, ctx: Optional[Context] = None) -> dict:
    if ctx is None:
        ctx = Context.default(DATASET_PACK_IDS)

    per_class_total = {c: 0 for c in CLASSES}
    per_class_hit = {c: 0 for c in CLASSES}
    clean_total = 0
    clean_fp = 0
    details = []

    for case in manifest.get("cases", []):
        snap = case["snapshot"]
        findings = gate_counted_dataset(verify_dataset(snap, ctx=ctx)["findings"])
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
    return {
        "recall": recall,
        "per_class_total": per_class_total,
        "per_class_hit": per_class_hit,
        "clean_total": clean_total,
        "clean_fp": clean_fp,
        "clean_fp_rate": clean_fp_rate,
        "details": details,
    }


def gate_e1(scored: dict, *, recall_floor: float = 0.90, fp_ceiling: float = 0.05) -> dict:
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
