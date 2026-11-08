"""Bench Part A: synthetic-release generator + scorer (SPEC.md §6)."""
from .dev_ext import generate_ext  # noqa: F401
from .generate import CLASSES, generate  # noqa: F401
from .score import gate1, lineage_walk_accuracy, score  # noqa: F401
