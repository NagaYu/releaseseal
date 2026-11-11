"""Verification core (SPEC.md §3–4; dataset W-checks §E1.3)."""
from .checks import Context  # noqa: F401
from .core import verify, verify_dataset  # noqa: F401
from .findings import (  # noqa: F401
    finding,
    gate_counted,
    gate_counted_dataset,
    make_evidence,
    max_severity,
    sev_rank,
)
from .wchecks import ALL_W_CHECKS, DATASET_PACK_IDS  # noqa: F401
