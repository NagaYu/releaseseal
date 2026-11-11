"""`local_dataset` adapter — build a ``dsnapshot/1`` from a dataset directory.

Reads the file inventory, the card (README front matter), a Croissant sidecar if
present, and streams row-oriented data files (jsonl/csv) to produce the pinned
``dsample/1`` content sample. Parquet/binary files are inventory-only (no stdlib
reader). Only small JSON/text is parsed; data files are read row-by-row for the
sample and hashed, never bulk-loaded into the snapshot (D-28/§E1.2).
"""
from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
import os
from typing import Optional

from .. import DSAMPLE_CAP_BYTES, DSAMPLE_CAP_ROWS, DSAMPLE_SEED
from . import cardparse
from .dsample import build_sample
from .dschema import croissant_subset, extract_declarations, finalize, make_dcard, make_dsnapshot, make_dsource

_HASH_CHUNK = 1024 * 1024
_SMALL_FILE_MAX = 2 * 1024 * 1024
_DATA_ROW_EXTS = (".jsonl", ".csv")
_DATA_EXTS = (".jsonl", ".csv", ".parquet", ".txt", ".json")


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_HASH_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_files(root: str):
    for dirpath, _dirs, names in os.walk(root):
        for name in sorted(names):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel == ".DS_Store":
                continue
            yield rel, full


def _split_name(rel: str) -> str:
    base = rel.rsplit("/", 1)[-1]
    for ext in _DATA_ROW_EXTS:
        if base.endswith(ext):
            return base[: -len(ext)]
    return base


def _read_rows(full: str, rel: str) -> list:
    rows = []
    try:
        if rel.endswith(".jsonl"):
            with open(full, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except ValueError:
                        obj = {"text": line}
                    rows.append(obj if isinstance(obj, dict) else {"text": str(obj)})
        elif rel.endswith(".csv"):
            with open(full, "r", encoding="utf-8", newline="") as fh:
                for obj in csv.DictReader(fh):
                    rows.append(dict(obj))
    except OSError:
        return []
    return rows


def snapshot_from_dir(path: str, *, captured_at: Optional[str] = None,
                      seed: int = DSAMPLE_SEED,
                      cap_rows: int = DSAMPLE_CAP_ROWS,
                      cap_bytes: int = DSAMPLE_CAP_BYTES) -> dict:
    captured_at = captured_at or _dt.date.today().isoformat()
    path = os.path.abspath(path)

    files = []
    by_rel = {}
    for rel, full in sorted(_iter_files(path), key=lambda x: x[0]):
        try:
            size = os.path.getsize(full)
            sha = _sha256_file(full)
        except OSError:
            size, sha = None, None
        files.append({"path": rel, "size": size, "sha256": sha, "hash_source": "streamed"})
        by_rel[rel] = full

    # Card
    yaml, prose = {}, ""
    for cand in ("README.md", "readme.md", "dataset_card.md"):
        if cand in by_rel:
            try:
                with open(by_rel[cand], "r", encoding="utf-8") as fh:
                    text = fh.read()
            except OSError:
                text = ""
            yaml, prose = cardparse.parse_front_matter(text)
            break
    card = make_dcard(yaml=yaml, prose=prose, declarations=extract_declarations(yaml))

    # Croissant sidecar
    croissant = None
    for cand in ("croissant.json", "croissant.jsonld"):
        if cand in by_rel and os.path.getsize(by_rel[cand]) <= _SMALL_FILE_MAX:
            try:
                with open(by_rel[cand], "r", encoding="utf-8") as fh:
                    croissant = croissant_subset(json.load(fh))
            except (OSError, ValueError):
                croissant = None
            break

    # LICENSE-file text for the W1 file-identification leg (Phase-E2). Small
    # files only; captured path-sorted. Absent -> key omitted -> leg silent.
    license_files = []
    for rel in sorted(by_rel):
        base = rel.rsplit("/", 1)[-1].upper()
        if not (base.startswith("LICENSE") or base.startswith("COPYING")):
            continue
        full = by_rel[rel]
        try:
            if os.path.getsize(full) > _SMALL_FILE_MAX:
                continue
            with open(full, "r", encoding="utf-8") as fh:
                txt = fh.read()
        except (OSError, ValueError):
            continue
        if txt.strip():
            license_files.append({"path": rel, "text": txt})

    # Rows per split + splits metadata
    rows_by_split = {}
    split_bytes = {}
    for rel, full in sorted(by_rel.items()):
        if rel.endswith(_DATA_ROW_EXTS):
            name = _split_name(rel)
            rows_by_split.setdefault(name, []).extend(_read_rows(full, rel))
            try:
                split_bytes[name] = split_bytes.get(name, 0) + os.path.getsize(full)
            except OSError:
                pass

    sample = build_sample(rows_by_split, seed=seed, cap_rows=cap_rows, cap_bytes=cap_bytes)
    splits = [{"name": name, "num_rows": len(rows_by_split[name]),
               "num_bytes": split_bytes.get(name)} for name in sorted(rows_by_split)]

    snap = make_dsnapshot(
        captured_at=captured_at,
        source=make_dsource("local_dataset", path=path),
        files=files,
        card=card,
        croissant=croissant,
        splits=splits,
        sample=sample,
        license_files=license_files or None,
    )
    return finalize(snap)
