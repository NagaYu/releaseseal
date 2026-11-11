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

# --- Extension E1 (dataset verification core) ------------------------------
DSNAPSHOT_SCHEMA = "dsnapshot/1"
PACK_SCHEMA_2 = "pack/2"
BENCH_MANIFEST_D_SCHEMA = "bench-manifest-d/1"
DSAMPLE_RULE = "dsample/1"
DSAMPLE_SEED = 20261111
DSAMPLE_CAP_ROWS = 2000
DSAMPLE_CAP_BYTES = 20 * 1024 * 1024
