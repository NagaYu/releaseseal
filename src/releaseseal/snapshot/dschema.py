"""Dataset-snapshot schema (``dsnapshot/1``) — SPEC.md §E1.1.

Dataset snapshots are plain JSON (dict) objects. This module provides
constructors, a validator, the closed-vocabulary declaration extractor
(§E1.1.1), and the content hash (D-09, shared helper, schema-agnostic).
"""
from __future__ import annotations

import copy
from typing import Any, Optional

from .. import DSNAPSHOT_SCHEMA
from .schema import content_hash  # shared D-09 helper (excludes snapshot_sha256)

# Re-export so dataset callers have one import site.
__all__ = [
    "content_hash", "finalize", "validate", "make_dsnapshot", "make_dsource",
    "empty_declarations", "extract_declarations", "make_dcard",
]

# ---------------------------------------------------------------------------
# Declarations (§E1.1.1) — the ONLY claim surface for W1–W7
# ---------------------------------------------------------------------------

def empty_declarations() -> dict:
    return {
        "license": None,
        "languages": [],
        "pii": None,
        "decontaminated_against": [],
        "dedup_rate": None,
        "sources": [],
        "file_inventory": [],
        "language_shares": {},
    }


def _as_str_or_none(v) -> Optional[str]:
    return v if isinstance(v, str) else None


def _norm_license(v) -> Optional[str]:
    if isinstance(v, str):
        return v.strip().lower()
    if isinstance(v, list) and v and isinstance(v[0], str):
        return v[0].strip().lower()
    return None


def _str_list(v) -> list:
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [x for x in v if isinstance(x, str)]
    return []


def extract_declarations(yaml: Optional[dict]) -> dict:
    """Deterministically extract the closed-vocabulary declarations from card
    YAML. A wrong-typed field yields its empty value and never raises (D-27):
    scalar → None, collection → []/{}.
    """
    d = empty_declarations()
    y = yaml if isinstance(yaml, dict) else {}
    ann = y.get("annotations")
    ann = ann if isinstance(ann, dict) else {}

    d["license"] = _norm_license(y.get("license"))
    d["languages"] = _str_list(y.get("language"))

    pii = ann.get("pii")
    d["pii"] = pii if pii in ("none", "present") else None

    d["decontaminated_against"] = _str_list(ann.get("decontaminated_against"))

    dr = ann.get("dedup_rate")
    if isinstance(dr, bool):
        dr = None  # bool is an int subclass; never a rate
    d["dedup_rate"] = float(dr) if isinstance(dr, (int, float)) and 0.0 <= dr <= 1.0 else None

    sources = []
    for item in ann.get("sources", []) if isinstance(ann.get("sources"), list) else []:
        if isinstance(item, dict) and isinstance(item.get("name"), str) and isinstance(item.get("license"), str):
            sources.append({"name": item["name"], "license": item["license"]})
    d["sources"] = sources

    inv = []
    for item in ann.get("file_inventory", []) if isinstance(ann.get("file_inventory"), list) else []:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            rows = item.get("rows")
            rows = rows if (isinstance(rows, int) and not isinstance(rows, bool)) else None
            inv.append({"path": item["path"], "rows": rows})
    d["file_inventory"] = inv

    shares = {}
    ls = ann.get("language_shares")
    if isinstance(ls, dict):
        for code, val in ls.items():
            if isinstance(code, str) and isinstance(val, (int, float)) and not isinstance(val, bool):
                shares[code] = float(val)
    d["language_shares"] = shares
    return d


def _norm_croissant_license(lic):
    """Normalize a Croissant ``license`` to an SPDX-ish id for the W1 leg
    (Phase-E2, D-39). HF auto-generated Croissant often carries the license as a
    URL (``https://choosealicense.com/licenses/apache-2.0/``) or SPDX URL; left
    raw it would manufacture spurious W1 inconsistencies against the plain card
    id. So: take the last path segment of a URL, drop a ``.html``/``.txt``/``.md``
    suffix, lowercase/strip. A plain id (bench data, author Croissant) is returned
    unchanged apart from case, so the bench is unaffected."""
    if isinstance(lic, list):
        lic = lic[0] if lic and isinstance(lic[0], str) else None
    if not isinstance(lic, str):
        return None
    v = lic.strip()
    if "://" in v or "/" in v:
        seg = v.rstrip("/").rsplit("/", 1)[-1]
        for suf in (".html", ".txt", ".md", ".json"):
            if seg.lower().endswith(suf):
                seg = seg[: -len(suf)]
        v = seg or v
    return v.strip().lower() or None


def croissant_subset(obj) -> Optional[dict]:
    """Extract only the Croissant keys W-checks read (§E1.1.2); else None."""
    if not isinstance(obj, dict):
        return None
    license_ = _norm_croissant_license(obj.get("license"))
    dist = []
    for d in obj.get("distribution", []) if isinstance(obj.get("distribution"), list) else []:
        if isinstance(d, dict):
            dist.append({"name": d.get("name"), "contentUrl": d.get("contentUrl"),
                         "sha256": d.get("sha256")})
    rs = []
    for r in obj.get("recordSet", []) if isinstance(obj.get("recordSet"), list) else []:
        if isinstance(r, dict):
            rs.append({"name": r.get("name")})
    return {"license": license_, "distribution": dist, "recordSet": rs}


# ---------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------

def make_dcard(yaml: Optional[dict] = None, prose: str = "",
               declarations: Optional[dict] = None) -> dict:
    y = yaml or {}
    return {
        "yaml": y,
        "prose": prose,
        "declarations": declarations if declarations is not None else extract_declarations(y),
    }


def make_dsource(adapter: str, *, repo_id=None, revision=None, path=None) -> dict:
    return {"adapter": adapter, "repo_id": repo_id, "revision": revision, "path": path}


def make_dsnapshot(
    *,
    captured_at: str,
    source: dict,
    files: Optional[list] = None,
    card: Optional[dict] = None,
    croissant: Optional[dict] = None,
    splits: Optional[list] = None,
    sample: Optional[dict] = None,
    license_files: Optional[list] = None,
) -> dict:
    snap: dict[str, Any] = {
        "schema_version": DSNAPSHOT_SCHEMA,
        "captured_at": captured_at,
        "source": source,
        "files": files or [],
        "card": card or make_dcard(),
        "croissant": croissant,
        "splits": splits or [],
        "sample": sample or {"rule": "dsample/1", "seed": None, "cap_rows": None,
                             "cap_bytes": None, "per_split": [], "rows": []},
        "snapshot_sha256": None,
    }
    # Optional LICENSE-file text carrier for the W1 file-identification leg
    # (§E1.3 W1, Phase-E2). The key is present ONLY when at least one LICENSE
    # file was captured, so snapshots without one (every Part A-D bench case)
    # stay byte-for-byte identical to Phase E1 (cases_sha256 unchanged).
    if license_files:
        clean = [
            {"path": lf["path"], "text": lf["text"]}
            for lf in license_files
            if isinstance(lf, dict) and isinstance(lf.get("path"), str) and isinstance(lf.get("text"), str)
        ]
        if clean:
            snap["license_files"] = clean
    return snap


def finalize(snapshot: dict) -> dict:
    """Return a copy with ``snapshot_sha256`` set to the content hash (D-09)."""
    out = copy.deepcopy(snapshot)
    out["snapshot_sha256"] = content_hash(out)
    return out


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_REQUIRED_TOP = {
    "schema_version", "captured_at", "source", "files", "card", "croissant",
    "splits", "sample", "snapshot_sha256",
}
_REQUIRED_DECL = set(empty_declarations().keys())


def validate(snapshot: dict) -> list[str]:
    """Return a list of human-readable schema errors (empty == valid)."""
    errs: list[str] = []
    if not isinstance(snapshot, dict):
        return ["dsnapshot is not an object"]
    if snapshot.get("schema_version") != DSNAPSHOT_SCHEMA:
        errs.append(f"schema_version must be {DSNAPSHOT_SCHEMA!r}")
    missing = _REQUIRED_TOP - set(snapshot)
    if missing:
        errs.append(f"missing top-level fields: {sorted(missing)}")
    src = snapshot.get("source")
    if not isinstance(src, dict) or src.get("adapter") not in ("hf_dataset", "local_dataset"):
        errs.append("source.adapter must be 'hf_dataset' or 'local_dataset'")
    if not isinstance(snapshot.get("files"), list):
        errs.append("files must be an array")
    card = snapshot.get("card")
    if not isinstance(card, dict):
        errs.append("card must be an object")
    else:
        decl = card.get("declarations")
        if not isinstance(decl, dict):
            errs.append("card.declarations must be an object")
        elif _REQUIRED_DECL - set(decl):
            errs.append(f"card.declarations missing: {sorted(_REQUIRED_DECL - set(decl))}")
    if not isinstance(snapshot.get("splits"), list):
        errs.append("splits must be an array")
    sample = snapshot.get("sample")
    if not isinstance(sample, dict) or not isinstance(sample.get("rows"), list):
        errs.append("sample must be an object with a 'rows' array")
    lf = snapshot.get("license_files")
    if lf is not None:  # optional (§E1.3 W1 file leg); absent on bench snapshots
        if not isinstance(lf, list) or not all(
            isinstance(x, dict) and isinstance(x.get("path"), str) and isinstance(x.get("text"), str)
            for x in lf
        ):
            errs.append("license_files, if present, must be a list of {path, text}")
    sh = snapshot.get("snapshot_sha256")
    if sh is not None and sh != content_hash(snapshot):
        errs.append("snapshot_sha256 does not match content")
    return errs
