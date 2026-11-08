"""Bench dev_ext — multi-level lineage cases (DECISIONS.md D-15; audit note 1).

Additive: the frozen 120-case dev split is untouched. These cases exercise V3's
recursive lineage walk (grandparent violations, unknown intermediates, deep
attribution failures, multi-parent merges, deep cleans) and carry a
``lineage_truth`` ground-truth set of violating ancestor ids for the
lineage-walk-accuracy metric. Each snapshot's ``lineage`` is supplied directly
(no fetch), so V3's compatible/incompatible/attribution logic is fully exercised.
"""
from __future__ import annotations

import random

from ..canonical import canonical_sha256
from ..snapshot.schema import finalize, make_file
from .generate import _build_clean


def _node(license_, depth, parent, notice=False):
    return {"license": license_, "notice_present_in_ancestor": notice,
            "depth": depth, "parent": parent, "resolved": True}


def _set_lineage(snap, declared, bases, lineage, *, notice_file=False):
    snap["card"]["claims"]["license"] = declared
    snap["card"]["yaml"]["license"] = declared
    snap["card"]["claims"]["base_model"] = list(bases)
    snap["card"]["yaml"]["base_model"] = list(bases)
    snap["card"]["claims"]["base_model_relation"] = "finetune"
    snap["card"]["yaml"]["base_model_relation"] = "finetune"
    snap["lineage"] = lineage
    if notice_file:
        snap["files"].append(make_file("NOTICE", size=256, sha256="n" * 64, hash_source="streamed"))
        snap["files"].sort(key=lambda f: f["path"])
    return snap


# Each scenario: (kind, expected, lineage_truth, mutate(snap)) where lineage_truth
# is the set of ancestor ids that are genuine violations (incompatible or
# attribution-missing); license_unknown is NOT a violation.

def _s_grandparent_violation(snap):
    _set_lineage(snap, "apache-2.0", ["p1"], {
        "p1": _node("apache-2.0", 1, None),
        "g1": _node("llama-3-community", 2, "p1"),
    })
    return "V3", ["V3"], ["g1"]


def _s_unknown_intermediate(snap):
    _set_lineage(snap, "apache-2.0", ["p1"], {
        "p1": _node("weird-custom-1.0", 1, None),      # not in license table
        "g1": _node("apache-2.0", 2, "p1"),
    })
    return "V3", ["V3"], []  # fires license_unknown, but no true violation


def _s_deep_attribution(snap):
    _set_lineage(snap, "gemma", ["p1"], {
        "p1": _node("gemma", 1, None, notice=False),
        "g1": _node("gemma", 2, "p1", notice=True),     # requires attribution, release has none
    })
    return "V3", ["V3"], ["g1"]


def _s_multiparent_one_bad(snap):
    _set_lineage(snap, "apache-2.0", ["a", "b"], {
        "a": _node("apache-2.0", 1, None),
        "b": _node("cc-by-nc-4.0", 1, None),            # non-commercial: apache not permitted
    })
    return "V3", ["V3"], ["b"]


def _s_deep_clean(snap):
    _set_lineage(snap, "apache-2.0", ["p1"], {
        "p1": _node("apache-2.0", 1, None),
        "g1": _node("apache-2.0", 2, "p1"),
    })
    return "clean", [], []


def _s_deep_clean_attrib_ok(snap):
    _set_lineage(snap, "gemma", ["p1"], {
        "p1": _node("gemma", 1, None),
        "g1": _node("gemma", 2, "p1", notice=True),
    }, notice_file=True)                                # NOTICE present -> attribution satisfied
    return "clean", [], []


SCENARIOS = [
    _s_grandparent_violation,
    _s_unknown_intermediate,
    _s_deep_attribution,
    _s_multiparent_one_bad,
    _s_deep_clean,
    _s_deep_clean_attrib_ok,
]


def generate_ext(seed: int = 0, per_scenario: int = 4) -> dict:
    rng = random.Random(seed ^ 0x5EED_E27)  # distinct stream from dev split
    cases = []
    idx = 0
    for scenario in SCENARIOS:
        for _ in range(per_scenario):
            idx += 1
            snap = _build_clean(rng, f"ext-{idx:04d}", profile="root")
            kind, expected, truth = scenario(snap)
            cases.append({
                "id": f"ext-{idx:04d}",
                "kind": kind,
                "expected": expected,
                "lineage_truth": truth,
                "snapshot": finalize(snap),
            })
    composition = {}
    for c in cases:
        composition[c["kind"]] = composition.get(c["kind"], 0) + 1
    return {
        "schema_version": "bench-manifest-ext/1",
        "seed": seed,
        "cases_sha256": canonical_sha256(cases),
        "composition": composition,
        "cases": cases,
    }
