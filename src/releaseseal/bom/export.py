"""Evidence pack -> CycloneDX 1.6 ML-BOM document — SPEC.md B.3.

The pack supplies release identity, snapshot kind, snapshot digest and findings.
The optional snapshot (D-42) supplies the file inventory (hashes where known) and
the declared license — a pack references its snapshot by hash and does not embed
the inventory. Deterministic: same inputs -> byte-identical document.
"""
from __future__ import annotations

from typing import Optional

_CDX_SPEC = "1.6"


def _snapshot_ref(pack: dict) -> dict:
    for rec in pack.get("records", []) if isinstance(pack.get("records"), list) else []:
        if isinstance(rec, dict) and rec.get("type") == "snapshot_ref":
            return rec
    return {}


def _release_kind(pack: dict, snap_ref: dict) -> str:
    """model / dataset. pack/1 -> model; pack/2 -> snapshot_ref.snapshot_kind."""
    kind = snap_ref.get("snapshot_kind")
    if kind in ("model", "dataset"):
        return kind
    return "dataset" if pack.get("schema_version") == "pack/2" else "model"


def _declared_license(snapshot: Optional[dict]) -> Optional[str]:
    if not isinstance(snapshot, dict):
        return None
    card = snapshot.get("card")
    if isinstance(card, dict):
        claims = card.get("claims")
        if isinstance(claims, dict) and isinstance(claims.get("license"), str):
            return claims["license"]
        decl = card.get("declarations")
        if isinstance(decl, dict) and isinstance(decl.get("license"), str):
            return decl["license"]
    return None


def _findings_summary(pack: dict) -> tuple[int, dict]:
    total = 0
    by_check: dict[str, int] = {}
    for rec in pack.get("records", []) if isinstance(pack.get("records"), list) else []:
        if isinstance(rec, dict) and rec.get("type") == "finding":
            f = rec.get("finding") or {}
            chk = f.get("check")
            if isinstance(chk, str):
                by_check[chk] = by_check.get(chk, 0) + 1
            total += 1
    return total, by_check


def export_bom(pack: dict, snapshot: Optional[dict] = None) -> dict:
    snap_ref = _snapshot_ref(pack)
    source = snap_ref.get("source") or {}
    repo_id = source.get("repo_id") if isinstance(source.get("repo_id"), str) else None
    revision = source.get("revision") if isinstance(source.get("revision"), str) else None

    if repo_id and revision:
        bom_ref = f"{repo_id}@{revision}"
    elif repo_id:
        bom_ref = repo_id
    else:
        bom_ref = "release"

    kind = _release_kind(pack, snap_ref)
    release: dict = {
        "bom-ref": bom_ref,
        "type": "machine-learning-model" if kind == "model" else "data",
        "name": repo_id or bom_ref,
    }
    if kind == "dataset":
        release["data"] = {"type": "dataset"}
    if revision:
        release["version"] = revision

    license_ = _declared_license(snapshot)
    if license_:
        release["licenses"] = [{"license": {"id": license_}}]

    # Properties: snapshot digest, chain tip, pack schema, findings summary.
    props: list[dict] = []
    digest = snap_ref.get("snapshot_sha256")
    if isinstance(digest, str):
        props.append({"name": "releaseseal:snapshot_sha256", "value": digest})
    if isinstance(pack.get("chain_tip"), str):
        props.append({"name": "releaseseal:chain_tip", "value": pack["chain_tip"]})
    if isinstance(pack.get("schema_version"), str):
        props.append({"name": "releaseseal:pack_schema", "value": pack["schema_version"]})
    total, by_check = _findings_summary(pack)
    props.append({"name": "releaseseal:finding_count", "value": str(total)})
    for chk in sorted(by_check):
        props.append({"name": f"releaseseal:findings:{chk}", "value": str(by_check[chk])})
    release["properties"] = props

    # File components: one per snapshot file with a known sha256 (path-sorted).
    components: list[dict] = []
    if isinstance(snapshot, dict) and isinstance(snapshot.get("files"), list):
        files = [f for f in snapshot["files"] if isinstance(f, dict) and isinstance(f.get("path"), str)]
        for f in sorted(files, key=lambda x: x["path"]):
            sha = f.get("sha256")
            if f.get("hash_source") not in (None, "none") and isinstance(sha, str) and sha:
                components.append({
                    "bom-ref": f["path"],
                    "type": "file",
                    "name": f["path"],
                    "hashes": [{"alg": "SHA-256", "content": sha}],
                })

    created_at = None
    header = next((r for r in pack.get("records", []) if isinstance(r, dict)
                   and r.get("type") == "header"), {})
    if isinstance(header, dict) and isinstance(header.get("created_at"), str):
        created_at = header["created_at"]

    metadata: dict = {"component": release}
    # A bare date (not a full datetime) is carried as a property, not as
    # metadata.timestamp, to keep output byte-deterministic (B.3).
    if created_at and "T" in created_at:
        metadata["timestamp"] = created_at
    elif created_at:
        props.append({"name": "releaseseal:created_at", "value": created_at})

    return {
        "bomFormat": "CycloneDX",
        "specVersion": _CDX_SPEC,
        "metadata": metadata,
        "components": components,
    }
