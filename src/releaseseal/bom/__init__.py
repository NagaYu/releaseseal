"""Module B — AIBOM import / export (SPEC.md Module B, extension design §4).

Independent of the V/W verification core: this subpackage reads AIBOM *documents*
(CycloneDX ML-BOM, SPDX 3.0 AI profile) and evidence packs, never
snapshots-under-verification. Decidable subset only; anything not decidable from
the bytes in front of it is `unverifiable`, never a finding and never a pass.
"""
from .facts import BOMFACTS_SCHEMA, import_bom  # noqa: F401
from .verify_bom import (  # noqa: F401
    BOM_RESULT_SCHEMA,
    artifacts_from_snapshot,
    verify_bom,
)
from .export import export_bom  # noqa: F401
