"""`hf` adapter — build a snapshot from Hugging Face Hub API metadata.

No weight downloads: file list + LFS SHA-256 come from the tree API; only small
config/card/result files are fetched. The code targets the real API, but the
fetcher is injectable so tests run entirely against recorded fixtures
(``FixtureFetcher``) with no network. A live ``HttpFetcher`` exists for the
optional, non-default smoke step only.
"""
from __future__ import annotations

import datetime as _dt
import json
from typing import Optional, Protocol

from . import cardparse
from .lineage import DEPTH_CAP, resolve_lineage
from .schema import finalize, make_card, make_file, make_snapshot, make_source

SMALL_FILE_MAX = 2 * 1024 * 1024
_SMALL_NAMES = (
    "config.json",
    "generation_config.json",
    "tokenizer_config.json",
    "model.safetensors.index.json",
)


class HFFetcher(Protocol):
    def model_info(self, repo: str, revision: Optional[str]) -> dict: ...
    def tree(self, repo: str, revision: Optional[str]) -> list: ...
    def file_text(self, repo: str, revision: Optional[str], path: str) -> Optional[str]: ...


class FixtureFetcher:
    """Serves recorded API responses from an in-memory bundle (see fixtures/hf).

    bundle = {"info": {...}, "tree": [...], "files": {path: text, ...}}

    Repo-aware: ``model_info`` serves the bundle only for its own repo id (or when
    the caller does not pin a repo); any *other* repo — e.g. an ancestor reached
    during recursive lineage resolution that is not in this single-repo fixture —
    raises ``KeyError`` so that ancestor stays honestly *unresolved* (D-14/D-07),
    never silently inheriting this model's license.
    """

    def __init__(self, bundle: dict):
        self._info = bundle.get("info", {})
        self._tree = bundle.get("tree", [])
        self._files = bundle.get("files", {})
        self._id = self._info.get("id")

    def _owns(self, repo) -> bool:
        return repo is None or self._id is None or repo == self._id

    def model_info(self, repo, revision):
        if not self._owns(repo):
            raise KeyError(f"repo {repo!r} not in fixture")
        return self._info

    def tree(self, repo, revision):
        return self._tree if self._owns(repo) else []

    def file_text(self, repo, revision, path):
        return self._files.get(path) if self._owns(repo) else None

    @classmethod
    def from_file(cls, path: str) -> "FixtureFetcher":
        with open(path, "r", encoding="utf-8") as fh:
            return cls(json.load(fh))


class MultiRepoFixtureFetcher:
    """Serves several repos' bundles keyed by repo id — used to exercise
    recursive multi-level lineage offline. bundles = {repo_id: bundle}.
    """

    def __init__(self, bundles: dict):
        self._f = {rid: FixtureFetcher(b if "info" in b else {"info": {"id": rid}, **b})
                   for rid, b in bundles.items()}
        # ensure each sub-fetcher knows its own id even if bundle omitted it
        for rid, f in self._f.items():
            if f._id is None:
                f._id = rid

    def _get(self, repo):
        if repo not in self._f:
            raise KeyError(f"repo {repo!r} not in fixture set")
        return self._f[repo]

    def model_info(self, repo, revision):
        return self._get(repo).model_info(repo, revision)

    def tree(self, repo, revision):
        return self._get(repo).tree(repo, revision)

    def file_text(self, repo, revision, path):
        return self._get(repo).file_text(repo, revision, path)

    @classmethod
    def from_file(cls, path: str) -> "MultiRepoFixtureFetcher":
        with open(path, "r", encoding="utf-8") as fh:
            return cls(json.load(fh))


def _read_json_text(text: Optional[str]) -> Optional[dict]:
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def build_snapshot(repo: str, revision: Optional[str], fetcher: HFFetcher,
                   *, captured_at: Optional[str] = None, lineage_depth: int = DEPTH_CAP) -> dict:
    captured_at = captured_at or _dt.date.today().isoformat()
    info = fetcher.model_info(repo, revision) or {}
    tree = fetcher.tree(repo, revision) or []
    resolved_rev = info.get("sha") or revision

    files = []
    present = set()
    for entry in tree:
        path = entry.get("path")
        if path is None:
            continue
        present.add(path)
        size = entry.get("size")
        lfs = entry.get("lfs") or {}
        if lfs.get("sha256"):
            files.append(make_file(path, size=lfs.get("size", size), sha256=lfs["sha256"], hash_source="lfs"))
        else:
            files.append(make_file(path, size=size, sha256=entry.get("sha256"),
                                   hash_source="lfs" if entry.get("sha256") else "none"))
    files.sort(key=lambda f: f["path"])

    # Card: cardData from API is already-parsed front matter.
    card_data = info.get("cardData") or {}
    readme = None
    for cand in ("README.md", "readme.md"):
        if cand in present:
            readme = fetcher.file_text(repo, resolved_rev, cand)
            break
    prose = ""
    if readme:
        _, prose = cardparse.split_front_matter(readme)
    claims = cardparse.extract_claims(card_data, prose)
    card = make_card(yaml=card_data, prose=prose, claims=claims)

    def fetch_small_json(name: str) -> Optional[dict]:
        if name not in present:
            return None
        return _read_json_text(fetcher.file_text(repo, resolved_rev, name))

    config = fetch_small_json("config.json")
    generation_config = fetch_small_json("generation_config.json")
    tokenizer_config = fetch_small_json("tokenizer_config.json")
    sti = fetch_small_json("model.safetensors.index.json")

    chat_template = None
    if isinstance(tokenizer_config, dict) and isinstance(tokenizer_config.get("chat_template"), str):
        chat_template = tokenizer_config["chat_template"]

    model_index = card_data.get("model-index") if isinstance(card_data.get("model-index"), list) else None

    result_files = {}
    for path in sorted(present):
        base = path.rsplit("/", 1)[-1].lower()
        if base.endswith(".json") and ("result" in base or "eval" in base):
            data = _read_json_text(fetcher.file_text(repo, resolved_rev, path))
            if data is not None:
                result_files[path] = data

    # Lineage: recursively resolve the base_model chain (D-14). Ancestors that
    # cannot be fetched, or whose license is unknown, stay unresolved -> V3
    # license_unknown (never guessed compatible).
    if isinstance(info.get("lineage"), dict) and info["lineage"]:
        lineage = info["lineage"]  # pre-flattened override (e.g. curated fixture)
    else:
        lineage = resolve_lineage(fetcher, claims.get("base_model") or [], depth=lineage_depth)

    snap = make_snapshot(
        captured_at=captured_at,
        source=make_source("hf", repo_id=repo, revision=resolved_rev),
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


def snapshot_from_fixture(path: str, repo: str, revision: Optional[str] = None,
                          *, captured_at: Optional[str] = None) -> dict:
    return build_snapshot(repo, revision, FixtureFetcher.from_file(path), captured_at=captured_at)
