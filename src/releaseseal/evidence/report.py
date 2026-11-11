"""Markdown report generated from an evidence pack (SPEC.md §7).

Wording discipline (design §1, §9): "evidence pack", never "certificate"; the
report states only documentation/artifact consistency, not legal compliance.
"""
from __future__ import annotations

from .. import APP_CODENAME
from ..verify.findings import SEVERITIES, sev_rank

_CHECK_TITLES = {
    "V1": "Artifact–record mismatch",
    "V2": "Architecture & scale claims",
    "V3": "License lineage",
    "V4": "Mandatory documentation gaps",
    "V5": "Staleness / revision drift",
    "V6": "Evaluation claim inconsistency",
    "V7": "Release completeness",
    "V8": "Undeclared derivation (heuristic signal)",
    "W1": "License consistency",
    "W2": "Declared source-license rollup",
    "W3": "Inventory truth",
    "W4": "PII falsification",
    "W5": "Benchmark contamination (measured)",
    "W6": "Dedup measurement",
    "W7": "Composition drift",
    "W8": "Dataset-card completeness (heuristic signal)",
}

_DATASET_CAVEAT = (
    "Dataset content checks (W4–W7) run on the pinned deterministic sample "
    "(`dsample/1`), not the full corpus. Absence of a PII/contamination/dedup "
    "finding means **none was detected in the sample**, never that the corpus is "
    "free of it; the pack does not certify absence."
)

_DISCLAIMER = (
    "This is an **evidence pack**, not a certificate. It reports the "
    "consistency and completeness of a release's documentation against its "
    "artifacts and against itself. It does **not** certify legal compliance, "
    "and does not verify the truth of training-data or capability claims."
)


def render_report(pack: dict) -> str:
    records = pack.get("records", [])
    header = next((r for r in records if r.get("type") == "header"), {})
    snap_ref = next((r for r in records if r.get("type") == "snapshot_ref"), {})
    findings = [r["finding"] for r in records if r.get("type") == "finding"]

    source = snap_ref.get("source", {})
    rel_id = source.get("repo_id") or source.get("path") or "(unknown release)"
    is_dataset = snap_ref.get("snapshot_kind") == "dataset"
    counted_label = "W1–W7" if is_dataset else "V1–V7"
    heur_label = "W8" if is_dataset else "V8"

    lines = [f"# {APP_CODENAME} evidence report", ""]
    lines.append(_DISCLAIMER)
    lines.append("")
    if is_dataset:
        lines.append(_DATASET_CAVEAT)
        lines.append("")
    lines.append("## Release")
    lines.append("")
    lines.append(f"- Release: `{rel_id}`")
    if source.get("revision"):
        lines.append(f"- Revision: `{source['revision']}`")
    lines.append(f"- Adapter: `{source.get('adapter', '?')}`")
    lines.append(f"- Snapshot SHA-256: `{snap_ref.get('snapshot_sha256')}`")
    lines.append(f"- Captured: {snap_ref.get('captured_at')}")
    lines.append(f"- Pack chain tip: `{pack.get('chain_tip')}`")
    lines.append("")

    if is_dataset:
        # Dataset gate/scorer counts non-heuristic, non-info (D-31); info
        # measurement findings (contamination_measured/dedup_measured) are shown
        # separately rather than as gate findings.
        gate_findings = [f for f in findings if not f.get("heuristic") and f["severity"] != "info"]
    else:
        gate_findings = [f for f in findings if not f.get("heuristic") and f["check"] != "V8"]
    by_sev = {s: sum(1 for f in gate_findings if f["severity"] == s) for s in SEVERITIES}
    n_heur = sum(1 for f in findings if f.get("heuristic"))
    n_info_meas = sum(1 for f in findings if not f.get("heuristic") and f["severity"] == "info")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Findings ({counted_label}): **{len(gate_findings)}** "
                 f"(high {by_sev['high']}, medium {by_sev['medium']}, low {by_sev['low']})")
    if is_dataset:
        lines.append(f"- Measurement findings (info, not gate-counted): {n_info_meas}")
    lines.append(f"- Heuristic signals ({heur_label}, not gate-counted): {n_heur}")
    packs = header.get("rule_packs", {})
    if packs:
        pv = ", ".join(f"`{k}`={v}" for k, v in sorted(packs.items()))
        lines.append(f"- Rule packs: {pv}")
    lines.append("")

    lines.append("## Findings")
    lines.append("")
    if not findings:
        lines.append("_No findings._")
    else:
        for check in sorted(set(f["check"] for f in findings), key=lambda c: c):
            group = [f for f in findings if f["check"] == check]
            group.sort(key=lambda f: -sev_rank(f["severity"]))
            lines.append(f"### {check} — {_CHECK_TITLES.get(check, check)}")
            lines.append("")
            for f in group:
                tag = " _(heuristic)_" if f.get("heuristic") else ""
                lines.append(f"- **[{f['severity']}]** `{f['code']}`{tag}: {f['message']}")
                ev = f.get("evidence") or {}
                bits = []
                if ev.get("file"):
                    bits.append(f"file `{ev['file']}`")
                if ev.get("field"):
                    bits.append(f"field `{ev['field']}`")
                if ev.get("expected") is not None:
                    bits.append(f"expected `{ev['expected']}`")
                if ev.get("actual") is not None:
                    bits.append(f"actual `{ev['actual']}`")
                if bits:
                    lines.append(f"  - evidence: {', '.join(bits)}")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"_Generated by {APP_CODENAME} from pack chain tip `{pack.get('chain_tip')}`. "
                 "Verify offline with `verify-pack`._")
    return "\n".join(lines) + "\n"
