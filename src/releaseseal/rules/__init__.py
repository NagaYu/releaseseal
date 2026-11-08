"""Rule packs (data files) + loader. Packs are versioned independently of code;
every finding set records the pack versions actually used (SPEC.md §5).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Optional

_PACKS_DIR = os.path.join(os.path.dirname(__file__), "packs")

# Default active packs for the standard verify profile.
# gpai-eu-v3 is the active EU pack (D-24/D-25): content-word matching + the
# 16-item single-source set. v1 (1.0.0) and v2 (2.0.0) are retained for the
# reproducibility of the Part B v1/v2 runs.
DEFAULT_PACK_IDS = ("hub-metadata-v1", "gpai-eu-v3", "license-terms-v1", "fingerprints-v1")


def pack_path(pack_id: str) -> str:
    return os.path.join(_PACKS_DIR, f"{pack_id}.json")


@lru_cache(maxsize=None)
def load_pack(pack_id: str) -> dict:
    with open(pack_path(pack_id), "r", encoding="utf-8") as fh:
        pack = json.load(fh)
    if pack.get("pack_id") != pack_id:
        raise ValueError(f"pack_id mismatch: file {pack_id} declares {pack.get('pack_id')!r}")
    return pack


def load_packs(pack_ids: Optional[tuple] = None) -> dict:
    """Return {pack_id: pack_dict} for the requested (default: all active) packs."""
    ids = pack_ids or DEFAULT_PACK_IDS
    return {pid: load_pack(pid) for pid in ids}


def pack_versions(packs: dict) -> dict:
    """{pack_id: version} for recording in finding sets / evidence packs."""
    return {pid: p.get("version") for pid, p in sorted(packs.items())}


# --- Authoring item-set single source (D-25) -------------------------------
def active_gpai_pack_id() -> str:
    for pid in DEFAULT_PACK_IDS:
        if pid.startswith("gpai-eu-"):
            return pid
    return "gpai-eu-v3"


def authoring_item_set():
    """The documentation item set (id, label, source, profile) — the SINGLE
    SOURCE for holdout-authoring briefs — taken from the active gpai pack (D-25).
    """
    pack = load_pack(active_gpai_pack_id())
    return [{"id": i["id"], "label": i["label"], "source": i["source"], "profile": i["profile"]}
            for i in pack["items"]]


def render_authoring_item_set_md() -> str:
    items = authoring_item_set()
    lines = [
        "# ReleaseSeal — documentation item set (authoring source of truth)",
        "",
        "Generated from the active EU rule pack (`" + active_gpai_pack_id() + "`) — do",
        "NOT edit by hand. These are the items a model-release card must document; a",
        "clean holdout card must contain all of them as content. The pack is the single",
        "source (DECISIONS.md D-25); a divergence test keeps this file in sync.",
        "",
        f"## Items ({len(items)})",
        "",
    ]
    for it in items:
        lines.append(f"- `{it['id']}` — {it['label']} ({it['source']}) [{it['profile']}]")
    lines.append("")
    return "\n".join(lines)
