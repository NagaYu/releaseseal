"""Release-snapshot schema (``snapshot/1``) — SPEC.md §2.

Snapshots are plain JSON (dict) objects so they serialize losslessly. This module
provides constructors, a validator, and the content-hash (D-09).
"""
from __future__ import annotations

import copy
from typing import Any, Optional

from .. import SNAPSHOT_SCHEMA
from ..canonical import canonical_sha256

# ---------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------

def make_file(
    path: str,
    size: Optional[int] = None,
    sha256: Optional[str] = None,
    hash_source: str = "none",
) -> dict:
    return {"path": path, "size": size, "sha256": sha256, "hash_source": hash_source}


def empty_claims() -> dict:
    return {
        "param_count": None,
        "param_count_text": None,
        "context_length": None,
        "architecture": None,
        "license": None,
        "base_model": [],
        "base_model_relation": None,
        "eval_claims": [],
    }


def make_card(yaml: Optional[dict] = None, prose: str = "", claims: Optional[dict] = None) -> dict:
    return {
        "yaml": yaml or {},
        "prose": prose,
        "claims": claims or empty_claims(),
    }


def make_snapshot(
    *,
    captured_at: str,
    source: dict,
    files: Optional[list] = None,
    card: Optional[dict] = None,
    config: Optional[dict] = None,
    generation_config: Optional[dict] = None,
    tokenizer_config: Optional[dict] = None,
    chat_template: Optional[str] = None,
    safetensors_index: Optional[dict] = None,
    model_index: Optional[list] = None,
    result_files: Optional[dict] = None,
    lineage: Optional[dict] = None,
) -> dict:
    snap: dict[str, Any] = {
        "schema_version": SNAPSHOT_SCHEMA,
        "captured_at": captured_at,
        "source": source,
        "files": files or [],
        "card": card or make_card(),
        "config": config,
        "generation_config": generation_config,
        "tokenizer_config": tokenizer_config,
        "chat_template": chat_template,
        "safetensors_index": safetensors_index,
        "model_index": model_index,
        "result_files": result_files or {},
        "lineage": lineage or {},
        "snapshot_sha256": None,
    }
    return snap


def make_source(adapter: str, *, repo_id=None, revision=None, path=None) -> dict:
    return {"adapter": adapter, "repo_id": repo_id, "revision": revision, "path": path}


# ---------------------------------------------------------------------------
# Hashing (D-09): hash content excluding the snapshot_sha256 field itself.
# ---------------------------------------------------------------------------

def content_hash(snapshot: dict) -> str:
    body = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    return canonical_sha256(body)


def finalize(snapshot: dict) -> dict:
    """Return a copy with ``snapshot_sha256`` set to the content hash."""
    out = copy.deepcopy(snapshot)
    out["snapshot_sha256"] = content_hash(out)
    return out


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_REQUIRED_TOP = {
    "schema_version", "captured_at", "source", "files", "card", "config",
    "generation_config", "tokenizer_config", "chat_template",
    "safetensors_index", "model_index", "result_files", "lineage",
    "snapshot_sha256",
}
_REQUIRED_CLAIMS = set(empty_claims().keys())


def validate(snapshot: dict) -> list[str]:
    """Return a list of human-readable schema errors (empty == valid)."""
    errs: list[str] = []
    if not isinstance(snapshot, dict):
        return ["snapshot is not an object"]
    if snapshot.get("schema_version") != SNAPSHOT_SCHEMA:
        errs.append(f"schema_version must be {SNAPSHOT_SCHEMA!r}")
    missing = _REQUIRED_TOP - set(snapshot)
    if missing:
        errs.append(f"missing top-level fields: {sorted(missing)}")
    src = snapshot.get("source")
    if not isinstance(src, dict) or "adapter" not in src:
        errs.append("source must be an object with an 'adapter' field")
    files = snapshot.get("files")
    if not isinstance(files, list):
        errs.append("files must be an array")
    else:
        for i, f in enumerate(files):
            if not isinstance(f, dict) or "path" not in f:
                errs.append(f"files[{i}] must be an object with a 'path'")
    card = snapshot.get("card")
    if not isinstance(card, dict):
        errs.append("card must be an object")
    else:
        claims = card.get("claims")
        if not isinstance(claims, dict):
            errs.append("card.claims must be an object")
        elif _REQUIRED_CLAIMS - set(claims):
            errs.append(f"card.claims missing: {sorted(_REQUIRED_CLAIMS - set(claims))}")
    sh = snapshot.get("snapshot_sha256")
    if sh is not None and sh != content_hash(snapshot):
        errs.append("snapshot_sha256 does not match content")
    return errs
