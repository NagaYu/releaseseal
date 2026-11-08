"""Verification core (SPEC.md §3–4)."""
from .checks import Context  # noqa: F401
from .core import verify  # noqa: F401
from .findings import finding, gate_counted, make_evidence, max_severity, sev_rank  # noqa: F401
