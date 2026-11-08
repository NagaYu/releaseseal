"""Evidence pack: hash-chained, schema-versioned record list (SPEC.md §7, D-05)."""
from __future__ import annotations

import datetime as _dt
from typing import Optional

from .. import APP_CODENAME, PACK_SCHEMA
from ..canonical import ZERO_HASH, canonical_sha256
from ..snapshot.schema import content_hash


def _chain(records: list) -> None:
    """Fill each record's ``prev`` in place (genesis = ZERO_HASH)."""
    prev = ZERO_HASH
    for rec in records:
        rec["prev"] = prev
        prev = canonical_sha256(rec)


def build_pack(snapshot: dict, findings_doc: dict, *, created_at: Optional[str] = None) -> dict:
    created_at = created_at or _dt.date.today().isoformat()
    source = snapshot.get("source") or {}
    snap_hash = snapshot.get("snapshot_sha256") or content_hash(snapshot)

    records: list = []
    records.append({
        "type": "header",
        "pack_schema": PACK_SCHEMA,
        "app": APP_CODENAME,
        "created_at": created_at,
        "rule_packs": findings_doc.get("rule_packs", {}),
    })
    records.append({
        "type": "snapshot_ref",
        "snapshot_sha256": snap_hash,
        "source": source,
        "captured_at": snapshot.get("captured_at"),
    })
    for f in findings_doc.get("findings", []):
        records.append({"type": "finding", "finding": f})

    _chain(records)
    return {
        "schema_version": PACK_SCHEMA,
        "chain_tip": canonical_sha256(records[-1]),
        "records": records,
    }


def verify_pack(pack: dict, snapshot: Optional[dict] = None) -> dict:
    """Recompute the hash chain (and optionally the snapshot hash). Offline.

    Returns {"ok": bool, "errors": [str], "findings": int, "snapshot_sha256": str|None}.
    """
    errors: list[str] = []
    records = pack.get("records")
    if pack.get("schema_version") != PACK_SCHEMA:
        errors.append(f"schema_version must be {PACK_SCHEMA!r}")
    if not isinstance(records, list) or not records:
        errors.append("pack has no records")
        return {"ok": False, "errors": errors, "findings": 0, "snapshot_sha256": None}

    prev = ZERO_HASH
    for i, rec in enumerate(records):
        if rec.get("prev") != prev:
            errors.append(f"record[{i}] prev mismatch (chain broken at or before this record)")
        prev = canonical_sha256(rec)
    if pack.get("chain_tip") != prev:
        errors.append("chain_tip does not match the final record (pack altered)")

    snap_ref = next((r for r in records if r.get("type") == "snapshot_ref"), None)
    snap_hash = snap_ref.get("snapshot_sha256") if snap_ref else None
    if snapshot is not None and snap_ref is not None:
        recomputed = content_hash(snapshot)
        if recomputed != snap_hash:
            errors.append("supplied snapshot does not match the pack's snapshot_sha256")

    n_findings = sum(1 for r in records if r.get("type") == "finding")
    return {"ok": not errors, "errors": errors, "findings": n_findings, "snapshot_sha256": snap_hash}
