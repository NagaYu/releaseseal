"""Bench Part A: synthetic-release generator + scorer (SPEC.md §6; dataset §E1.7)."""
from .dev_ext import generate_ext  # noqa: F401
from .generate import CLASSES, generate  # noqa: F401
from .score import gate1, lineage_walk_accuracy, score  # noqa: F401

# --- Extension E1: Part A-D (dataset) --------------------------------------
from .generate_d import CLASSES as CLASSES_D, generate as generate_d  # noqa: F401
from .score_d import gate_e1, score as score_d  # noqa: F401
