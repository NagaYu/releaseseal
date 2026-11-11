"""Sampling rule ``dsample/1`` (SPEC.md §E1.2) — pinned, implemented once.

Shared by both dataset adapters and the Part A-D bench generator. Deterministic:
same input + same seed → byte-identical sample (D-28).
"""
from __future__ import annotations

import hashlib
import random
from typing import Optional

from .. import DSAMPLE_CAP_BYTES, DSAMPLE_CAP_ROWS, DSAMPLE_RULE, DSAMPLE_SEED
from ..canonical import canonical_bytes

# Text-field name preference (first matching STRING field wins), pinned order.
_TEXT_FIELDS = ("text", "content", "prompt", "completion", "instruction")


def _split_seed(seed: int, name: str) -> int:
    """Per-split RNG seed derived with sha256 (not Python's salted hash) so the
    reservoir is reproducible across processes (D-28)."""
    digest = hashlib.sha256(f"{seed}:{name}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def row_text(row: dict) -> str:
    """The row's designated text (§E1.2): first string field named one of the
    preferred names, else the row serialized as canonical JSON."""
    if isinstance(row, dict):
        for key in _TEXT_FIELDS:
            v = row.get(key)
            if isinstance(v, str):
                return v
    return canonical_bytes(row).decode("utf-8")


def _reservoir(indices_rows, cap_rows: int, rng: random.Random):
    """Algorithm R over an iterable of (index, row); retained list is returned
    sorted by ascending index."""
    reservoir = []
    for i, (idx, row) in enumerate(indices_rows):
        if i < cap_rows:
            reservoir.append((idx, row))
        else:
            j = rng.randint(0, i)
            if j < cap_rows:
                reservoir[j] = (idx, row)
    reservoir.sort(key=lambda t: t[0])
    return reservoir


def build_sample(rows_by_split: dict, *, seed: int = DSAMPLE_SEED,
                 cap_rows: int = DSAMPLE_CAP_ROWS,
                 cap_bytes: int = DSAMPLE_CAP_BYTES,
                 rows_total_by_split: Optional[dict] = None) -> dict:
    """Build the ``dsample/1`` record.

    ``rows_by_split`` maps split name -> list of row dicts in file order.
    ``rows_total_by_split`` (optional) overrides the reported total (e.g. when the
    adapter streamed only part of a large file); default is the provided length.
    """
    rows_total_by_split = rows_total_by_split or {}
    per_split = []
    retained = []  # (split, index, row) in (split-name, index) order
    for name in sorted(rows_by_split):
        rows = rows_by_split[name] or []
        rng = random.Random(_split_seed(seed, name))
        res = _reservoir(enumerate(rows), cap_rows, rng)
        for idx, row in res:
            retained.append((name, idx, row))

    # Enforce the byte cap in (split-name, index) order; skip overflowing rows.
    out_rows = []
    sampled_bytes = {name: 0 for name in rows_by_split}
    sampled_count = {name: 0 for name in rows_by_split}
    cumulative = 0
    for name, idx, row in retained:
        text = row_text(row)
        nbytes = len(text.encode("utf-8"))
        if cumulative + nbytes > cap_bytes:
            continue
        cumulative += nbytes
        sampled_bytes[name] += nbytes
        sampled_count[name] += 1
        out_rows.append({"split": name, "index": idx, "text": text})

    for name in sorted(rows_by_split):
        total = rows_total_by_split.get(name)
        if total is None:
            total = len(rows_by_split[name] or [])
        per_split.append({
            "split": name,
            "rows_total": total,
            "rows_sampled": sampled_count[name],
            "bytes_read": sampled_bytes[name],
        })

    return {
        "rule": DSAMPLE_RULE,
        "seed": seed,
        "cap_rows": cap_rows,
        "cap_bytes": cap_bytes,
        "per_split": per_split,
        "rows": out_rows,
    }
