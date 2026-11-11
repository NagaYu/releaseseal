"""`hf_dataset` adapter — build a ``dsnapshot/1`` from HF dataset-repo metadata.

No bulk downloads: file list + LFS SHA-256 from the tree API, card YAML +
Croissant where present, split/row metadata, and a pinned content sample. The
fetcher is injectable so tests run entirely against recorded fixtures
(``DatasetFixtureFetcher``) with no network (D-11 discipline carried over).

Recorded bundle shape (``fixtures/hf/dataset-*.json``):

    {
      "info":   {"id": repo, "sha": rev, "cardData": {...}},   # cardData = parsed front matter
      "tree":   [{"path", "size", "lfs": {"sha256", "size"}}, ...],
      "files":  {path: text, ...},                              # small files (README/croissant)
      "splits": [{"name", "num_rows", "num_bytes"}, ...],
      "rows":   {split: [row dict, ...], ...},                  # the content-sample source
      "croissant": {...}                                        # optional; else files["croissant.json"]
    }
"""
from __future__ import annotations

import datetime as _dt
import json
from typing import Optional

from .. import DSAMPLE_CAP_BYTES, DSAMPLE_CAP_ROWS, DSAMPLE_SEED
from .dsample import build_sample
from .dschema import croissant_subset, extract_declarations, finalize, make_dcard, make_dsnapshot, make_dsource

_LICENSE_TEXT_MAX = 64 * 1024  # LICENSE files are small; cap defensively


def _is_license_path(path: str) -> bool:
    """A repo-relative path that names a LICENSE/COPYING file (W1 file leg)."""
    base = path.rsplit("/", 1)[-1].upper()
    return base.startswith("LICENSE") or base.startswith("COPYING")


class DatasetFixtureFetcher:
    """Serves one recorded dataset bundle from memory (no network)."""

    def __init__(self, bundle: dict):
        self._b = bundle or {}

    @classmethod
    def from_file(cls, path: str) -> "DatasetFixtureFetcher":
        with open(path, "r", encoding="utf-8") as fh:
            return cls(json.load(fh))

    def info(self, repo, revision):
        return self._b.get("info", {})

    def tree(self, repo, revision):
        return self._b.get("tree", [])

    def file_text(self, repo, revision, path):
        return (self._b.get("files") or {}).get(path)

    def splits(self, repo, revision):
        return self._b.get("splits", [])

    def rows(self, repo, revision):
        return self._b.get("rows", {})

    def croissant(self, repo, revision):
        return self._b.get("croissant")


def build_dataset_snapshot(repo: str, revision: Optional[str], fetcher,
                           *, captured_at: Optional[str] = None,
                           seed: int = DSAMPLE_SEED,
                           cap_rows: int = DSAMPLE_CAP_ROWS,
                           cap_bytes: int = DSAMPLE_CAP_BYTES) -> dict:
    captured_at = captured_at or _dt.date.today().isoformat()
    info = fetcher.info(repo, revision) or {}
    tree = fetcher.tree(repo, revision) or []
    resolved_rev = info.get("sha") or revision

    files = []
    present = set()
    for entry in tree:
        path = entry.get("path")
        if path is None:
            continue
        present.add(path)
        lfs = entry.get("lfs") or {}
        if lfs.get("sha256"):
            files.append({"path": path, "size": lfs.get("size", entry.get("size")),
                          "sha256": lfs["sha256"], "hash_source": "lfs"})
        else:
            sha = entry.get("sha256")
            files.append({"path": path, "size": entry.get("size"), "sha256": sha,
                          "hash_source": "lfs" if sha else "none"})
    files.sort(key=lambda f: f["path"])

    card_data = info.get("cardData") or {}
    prose = ""
    for cand in ("README.md", "readme.md"):
        if cand in present:
            text = fetcher.file_text(repo, resolved_rev, cand)
            if isinstance(text, str):
                from . import cardparse
                _, prose = cardparse.split_front_matter(text)
            break
    card = make_dcard(yaml=card_data, prose=prose, declarations=extract_declarations(card_data))

    # LICENSE-file text for the W1 file-identification leg (Phase-E2). Small
    # files only (same no-weights discipline); captured path-sorted so the first
    # that identifies is deterministic. Absent -> key omitted -> leg silent.
    license_files = []
    for path in sorted(present):
        if _is_license_path(path):
            txt = fetcher.file_text(repo, resolved_rev, path)
            if isinstance(txt, str) and txt.strip():
                license_files.append({"path": path, "text": txt[:_LICENSE_TEXT_MAX]})

    croissant = fetcher.croissant(repo, resolved_rev)
    if croissant is None:
        for cand in ("croissant.json", "croissant.jsonld"):
            if cand in present:
                txt = fetcher.file_text(repo, resolved_rev, cand)
                try:
                    croissant = json.loads(txt) if isinstance(txt, str) else None
                except ValueError:
                    croissant = None
                break
    croissant = croissant_subset(croissant)

    rows_by_split = {k: list(v) for k, v in (fetcher.rows(repo, resolved_rev) or {}).items()}
    sample = build_sample(rows_by_split, seed=seed, cap_rows=cap_rows, cap_bytes=cap_bytes)

    splits = []
    for s in fetcher.splits(repo, resolved_rev) or []:
        if isinstance(s, dict) and isinstance(s.get("name"), str):
            splits.append({"name": s["name"], "num_rows": s.get("num_rows"),
                           "num_bytes": s.get("num_bytes")})
    if not splits:
        splits = [{"name": name, "num_rows": len(rows_by_split[name]), "num_bytes": None}
                  for name in sorted(rows_by_split)]

    snap = make_dsnapshot(
        captured_at=captured_at,
        source=make_dsource("hf_dataset", repo_id=repo, revision=resolved_rev),
        files=files,
        card=card,
        croissant=croissant,
        splits=splits,
        sample=sample,
        license_files=license_files or None,
    )
    return finalize(snap)


def snapshot_from_dataset_fixture(path: str, repo: str, revision: Optional[str] = None,
                                  *, captured_at: Optional[str] = None) -> dict:
    return build_dataset_snapshot(repo, revision, DatasetFixtureFetcher.from_file(path),
                                  captured_at=captured_at)
