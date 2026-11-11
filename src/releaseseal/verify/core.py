"""Verification core: ``snapshot JSON -> findings JSON`` (pure, deterministic).

SPEC.md §1, §3. The only entry point the CLI / bench / packs call.
"""
from __future__ import annotations

from typing import Optional

from .. import DSNAPSHOT_SCHEMA, FINDINGS_SCHEMA
from .checks import ALL_CHECKS, Context
from .wchecks import ALL_W_CHECKS, DATASET_PACK_IDS


def verify(snapshot: dict, *, ctx: Optional[Context] = None,
           pack_ids=None, as_of_now: Optional[str] = None) -> dict:
    """Run the appropriate check suite over ``snapshot`` and return findings.

    Dispatches on ``schema_version``: ``dsnapshot/1`` -> dataset W1–W8,
    everything else -> model V1–V8. Deterministic: identical ``snapshot`` +
    packs + ``as_of_now`` -> identical output.
    """
    if snapshot.get("schema_version") == DSNAPSHOT_SCHEMA:
        return verify_dataset(snapshot, ctx=ctx, pack_ids=pack_ids, as_of_now=as_of_now)

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


def verify_dataset(snapshot: dict, *, ctx: Optional[Context] = None,
                   pack_ids=None, as_of_now: Optional[str] = None) -> dict:
    """Run dataset W1–W8 over a ``dsnapshot/1`` and return a findings document."""
    if ctx is None:
        ctx = Context.default(pack_ids or DATASET_PACK_IDS)
    if as_of_now is not None:
        ctx = Context(packs=ctx.packs, as_of_now=as_of_now)

    findings = []
    for check in ALL_W_CHECKS:
        findings.extend(check(snapshot, ctx))

    return {
        "schema_version": FINDINGS_SCHEMA,
        "rule_packs": ctx.versions(),
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
        "findings": findings,
    }
