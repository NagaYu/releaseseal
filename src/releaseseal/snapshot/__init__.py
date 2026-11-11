"""Snapshot layer: schema + adapters (SPEC.md §2)."""
from . import cardparse, schema  # noqa: F401
from .hf_adapter import (  # noqa: F401
    FixtureFetcher,
    MultiRepoFixtureFetcher,
    build_snapshot as build_hf_snapshot,
    snapshot_from_fixture,
)
from .lineage import resolve_lineage  # noqa: F401
from .local_adapter import snapshot_from_dir  # noqa: F401
from .schema import content_hash, finalize, make_snapshot, validate  # noqa: F401

# --- Extension E1: dataset snapshot layer ----------------------------------
from . import dschema, dsample  # noqa: F401
from .dschema import (  # noqa: F401
    extract_declarations,
    make_dsnapshot,
    validate as validate_dsnapshot,
)
from .dsample import build_sample  # noqa: F401
from .hf_dataset import (  # noqa: F401
    DatasetFixtureFetcher,
    build_dataset_snapshot,
    snapshot_from_dataset_fixture,
)
from .local_dataset import snapshot_from_dir as snapshot_dataset_from_dir  # noqa: F401
