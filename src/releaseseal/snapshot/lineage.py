"""Recursive base_model lineage resolution (DECISIONS.md D-14; closes audit note 1).

Walks the ``base_model`` chain to a depth cap with a cycle guard, flattening every
ancestor into the snapshot ``lineage`` map so V3 can check the declared license
against *all* ancestors, not just direct parents. Unreachable ancestors and
licenses absent from the license-terms table are left unresolved (license None),
which V3 renders as ``license_unknown`` — never a guessed-compatible verdict.
"""
from __future__ import annotations

from collections import deque
from typing import Optional

DEPTH_CAP = 8


def _norm_license(val) -> Optional[str]:
    if isinstance(val, str):
        return val.strip().lower() or None
    if isinstance(val, list) and val and isinstance(val[0], str):
        return val[0].strip().lower() or None
    return None


def _card_license(info: dict) -> Optional[str]:
    cd = info.get("cardData") or {}
    return _norm_license(cd.get("license"))


def _card_bases(info: dict) -> list:
    cd = info.get("cardData") or {}
    bm = cd.get("base_model")
    if bm is None:
        return []
    if isinstance(bm, list):
        return [str(x) for x in bm if x]
    return [str(bm)]


def _is_notice(path: str) -> bool:
    # Mirror the release-side detector (checks._has_notice): NOTICE/ATTRIBUTION
    # only. A plain LICENSE file is not an attribution NOTICE and must not count,
    # or attribution_missing would over-fire on real finetunes.
    base = path.rsplit("/", 1)[-1].upper()
    return base.startswith("NOTICE") or base.startswith("ATTRIBUTION")


def resolve_lineage(fetcher, base_models, *, depth: int = DEPTH_CAP) -> dict:
    """Return a flattened ancestor map.

    ``{ancestor_id: {license, notice_present_in_ancestor, depth, parent,
    resolved}}``. ``resolved`` is False when the ancestor could not be fetched.
    """
    lineage: dict = {}
    visited: set = set()
    q = deque((str(b), 1, None) for b in (base_models or []) if b)

    while q:
        repo, d, parent = q.popleft()
        if repo in visited:
            continue
        visited.add(repo)
        node = {"license": None, "notice_present_in_ancestor": None,
                "depth": d, "parent": parent, "resolved": False}
        info = None
        try:
            info = fetcher.model_info(repo, None)
        except Exception:
            info = None
        if info:
            node["resolved"] = True
            node["license"] = _card_license(info)
            try:
                tree = fetcher.tree(repo, None) or []
            except Exception:
                tree = []
            node["notice_present_in_ancestor"] = any(
                _is_notice(e.get("path", "")) for e in tree if isinstance(e, dict)
            )
            if d < depth:
                for b in _card_bases(info):
                    if b not in visited:
                        q.append((b, d + 1, repo))
        lineage[repo] = node
    return lineage
