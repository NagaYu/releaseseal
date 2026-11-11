"""Evidence pack: hash-chained, schema-versioned record list (SPEC.md §7, D-05)."""
from __future__ import annotations

import datetime as _dt
from typing import Optional

from .. import APP_CODENAME, DSNAPSHOT_SCHEMA, PACK_SCHEMA, PACK_SCHEMA_2
from ..canonical import ZERO_HASH, canonical_sha256
from ..snapshot.schema import content_hash

_VALID_PACK_SCHEMAS = (PACK_SCHEMA, PACK_SCHEMA_2)


def _chain(records: list) -> None:
    """Fill each record's ``prev`` in place (genesis = ZERO_HASH)."""
    prev = ZERO_HASH
    for rec in records:
        rec["prev"] = prev
        prev = canonical_sha256(rec)


def build_pack(snapshot: dict, findings_doc: dict, *, created_at: Optional[str] = None) -> dict:
    """Build an evidence pack.

    Model snapshots (``snapshot/1``) take the ``pack/1`` path **byte-for-byte as
    before** (D-35); dataset snapshots (``dsnapshot/1``) take the ``pack/2`` path,
    whose ``snapshot_ref`` carries ``snapshot_kind``. The ``content_hash`` helper
    is schema-agnostic (it excludes only ``snapshot_sha256``).
    """
    created_at = created_at or _dt.date.today().isoformat()
    source = snapshot.get("source") or {}
    snap_hash = snapshot.get("snapshot_sha256") or content_hash(snapshot)
    is_dataset = snapshot.get("schema_version") == DSNAPSHOT_SCHEMA
    pack_schema = PACK_SCHEMA_2 if is_dataset else PACK_SCHEMA

    records: list = []
    records.append({
        "type": "header",
        "pack_schema": pack_schema,
        "app": APP_CODENAME,
        "created_at": created_at,
        "rule_packs": findings_doc.get("rule_packs", {}),
    })
    snap_ref = {
        "type": "snapshot_ref",
        "snapshot_sha256": snap_hash,
        "source": source,
        "captured_at": snapshot.get("captured_at"),
    }
    if is_dataset:
        # pack/2 only: keep model packs byte-for-byte identical to pack/1 (D-35).
        snap_ref["snapshot_kind"] = "dataset"
    records.append(snap_ref)
    for f in findings_doc.get("findings", []):
        records.append({"type": "finding", "finding": f})

    _chain(records)
    return {
        "schema_version": pack_schema,
        "chain_tip": canonical_sha256(records[-1]),
        "records": records,
    }


def verify_pack(pack: dict, snapshot: Optional[dict] = None) -> dict:
    """Recompute the hash chain (and optionally the snapshot hash). Offline.

    Returns {"ok": bool, "errors": [str], "findings": int, "snapshot_sha256": str|None}.
    """
    errors: list[str] = []
    records = pack.get("records")
    if pack.get("schema_version") not in _VALID_PACK_SCHEMAS:
        errors.append(f"schema_version must be one of {list(_VALID_PACK_SCHEMAS)}")
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
