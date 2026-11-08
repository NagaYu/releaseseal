"""Finding schema + severity helpers (SPEC.md §4, DECISIONS.md D-03, D-04)."""
from __future__ import annotations

from typing import Optional

SEVERITIES = ("info", "low", "medium", "high")
_SEV_RANK = {s: i for i, s in enumerate(SEVERITIES)}


def sev_rank(sev: str) -> int:
    return _SEV_RANK.get(sev, 0)


def make_evidence(file: Optional[str] = None, field: Optional[str] = None,
                  expected=None, actual=None) -> dict:
    def _s(v):
        return None if v is None else str(v)
    return {"file": file, "field": field, "expected": _s(expected), "actual": _s(actual)}


def finding(check: str, code: str, severity: str, message: str,
            *, heuristic: bool = False, evidence: Optional[dict] = None,
            subject: Optional[str] = None) -> dict:
    if severity not in _SEV_RANK:
        raise ValueError(f"bad severity {severity!r}")
    return {
        "check": check,
        "code": code,
        "severity": severity,
        "heuristic": bool(heuristic),
        "message": message,
        "evidence": evidence or make_evidence(),
        # Optional structured subject the finding is about (e.g. a lineage
        # ancestor id for V3). Nullable; consumers may ignore it (SPEC.md §4).
        "subject": subject,
    }


def gate_counted(findings: list) -> list:
    """Findings that count toward gates/CI rollups: V1–V7, non-heuristic (D-03)."""
    return [f for f in findings if not f.get("heuristic") and f["check"] != "V8"]


def max_severity(findings: list) -> Optional[str]:
    counted = gate_counted(findings)
    if not counted:
        return None
    return max(counted, key=lambda f: sev_rank(f["severity"]))["severity"]
