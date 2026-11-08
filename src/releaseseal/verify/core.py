"""Verification core: ``snapshot JSON -> findings JSON`` (pure, deterministic).

SPEC.md §1, §3. The only entry point the CLI / bench / packs call.
"""
from __future__ import annotations

from typing import Optional

from .. import FINDINGS_SCHEMA
from .checks import ALL_CHECKS, Context


def verify(snapshot: dict, *, ctx: Optional[Context] = None,
           pack_ids=None, as_of_now: Optional[str] = None) -> dict:
    """Run V1–V8 over ``snapshot`` and return a findings document.

    Deterministic: identical ``snapshot`` + packs + ``as_of_now`` -> identical output.
    """
    if ctx is None:
        ctx = Context.default(pack_ids)
    if as_of_now is not None:
        ctx = Context(packs=ctx.packs, as_of_now=as_of_now)

    findings = []
    for check in ALL_CHECKS:
        findings.extend(check(snapshot, ctx))

    return {
        "schema_version": FINDINGS_SCHEMA,
        "rule_packs": ctx.versions(),
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
        "findings": findings,
    }
