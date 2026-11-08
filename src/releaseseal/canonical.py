"""Canonical JSON serialization and hashing (DECISIONS.md D-09).

Centralised so every hash in the system (snapshot identity, pack chain, bench
cases) is computed identically and deterministically.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

ZERO_HASH = "0" * 64


def canonical_bytes(obj: Any) -> bytes:
    """Deterministic UTF-8 bytes for ``obj``: sorted keys, no whitespace."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(obj: Any) -> str:
    """sha256 of the canonical JSON of ``obj``."""
    return sha256_hex(canonical_bytes(obj))
