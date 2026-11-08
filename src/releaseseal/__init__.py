"""ReleaseSeal — offline model-release documentation/artifact verifier.

Public name "ReleaseSeal" (chosen 2026-11-08; was codename "ModelPass" — see
DECISIONS.md D-01 and D-13). The name is confined here and in packaging only;
modules never hard-code it, they read it from the two constants below.
"""

# --- Product name (change these two + pyproject on rename; D-01) ------------
APP_CODENAME = "ReleaseSeal"
APP_SLUG = "releaseseal"
# ---------------------------------------------------------------------------

__version__ = "0.1.0"

SNAPSHOT_SCHEMA = "snapshot/1"
FINDINGS_SCHEMA = "findings/1"
PACK_SCHEMA = "pack/1"
BENCH_MANIFEST_SCHEMA = "bench-manifest/1"
