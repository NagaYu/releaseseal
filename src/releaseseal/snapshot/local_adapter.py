"""`local` adapter — build a snapshot from a release directory (SPEC.md §2).

The only mode that touches weight bytes, and only to stream a SHA-256 on the
user's own machine. No file content beyond small JSON/text config is parsed.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from typing import Optional

from . import cardparse
from .schema import finalize, make_card, make_file, make_snapshot, make_source

# Only parse (read into JSON/text) files at or below this size; others are
# hashed but their content is never loaded (weight-file discipline).
SMALL_FILE_MAX = 2 * 1024 * 1024  # 2 MiB
_HASH_CHUNK = 1024 * 1024


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_HASH_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _iter_files(root: str):
    for dirpath, _dirs, names in os.walk(root):
        for name in sorted(names):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel == ".DS_Store":
                continue
            yield rel, full


def snapshot_from_dir(path: str, *, captured_at: Optional[str] = None) -> dict:
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
        files.append(make_file(rel, size=size, sha256=sha, hash_source="streamed"))
        by_rel[rel] = full

    # Card
    yaml, prose, claims = {}, "", None
    for cand in ("README.md", "readme.md", "MODEL_CARD.md"):
        if cand in by_rel:
            try:
                with open(by_rel[cand], "r", encoding="utf-8") as fh:
                    text = fh.read()
            except OSError:
                text = ""
            yaml, prose = cardparse.parse_front_matter(text)
            claims = cardparse.extract_claims(yaml, prose)
            break
    card = make_card(yaml=yaml, prose=prose, claims=claims)

    def load_small(rel: str) -> Optional[dict]:
        full = by_rel.get(rel)
        if full and os.path.getsize(full) <= SMALL_FILE_MAX:
            return _read_json(full)
        return None

    config = load_small("config.json")
    generation_config = load_small("generation_config.json")
    tokenizer_config = load_small("tokenizer_config.json")
    sti = load_small("model.safetensors.index.json")

    chat_template = None
    if isinstance(tokenizer_config, dict) and isinstance(tokenizer_config.get("chat_template"), str):
        chat_template = tokenizer_config["chat_template"]
    elif "chat_template.jinja" in by_rel:
        try:
            with open(by_rel["chat_template.jinja"], "r", encoding="utf-8") as fh:
                chat_template = fh.read()
        except OSError:
            chat_template = None

    model_index = card["yaml"].get("model-index") if isinstance(card["yaml"].get("model-index"), list) else None

    result_files = {}
    for rel in by_rel:
        base = rel.rsplit("/", 1)[-1].lower()
        if base.endswith(".json") and ("result" in base or "eval" in base):
            data = load_small(rel)
            if data is not None:
                result_files[rel] = data

    lineage = _read_json(by_rel["lineage.json"]) if "lineage.json" in by_rel else {}
    if not isinstance(lineage, dict):
        lineage = {}

    snap = make_snapshot(
        captured_at=captured_at,
        source=make_source("local", path=path),
        files=files,
        card=card,
        config=config,
        generation_config=generation_config,
        tokenizer_config=tokenizer_config,
        chat_template=chat_template,
        safetensors_index=sti,
        model_index=model_index,
        result_files=result_files,
        lineage=lineage,
    )
    return finalize(snap)
