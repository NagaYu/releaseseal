"""BOM document -> facts (`bomfacts/1`) — SPEC.md B.1.

Two source formats: CycloneDX ML-BOM (JSON, spec 1.5/1.6/1.7) and SPDX 3.0 AI
profile (JSON-LD). The format is detected from the document *shape*, never from a
filename. Import is a faithful transcription into a fixed facts shape; a shape
that cannot be mapped is counted (`ignored` for CycloneDX other-typed components,
`unmapped` for SPDX elements), never guessed.

Deterministic: same document -> byte-identical facts (component order is document
order; D-09 sorts keys at serialization time).
"""
from __future__ import annotations

from typing import Any, Optional

BOMFACTS_SCHEMA = "bomfacts/1"

_CYCLONEDX_SPECS = {"1.5": "cyclonedx-1.5", "1.6": "cyclonedx-1.6", "1.7": "cyclonedx-1.7"}
_WEIGHT_DATASET_TYPE = "data"


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def detect_format(document: Any) -> Optional[str]:
    """Return ``"cyclonedx"`` / ``"spdx"`` / ``None`` from the document shape."""
    if not isinstance(document, dict):
        return None
    if str(document.get("bomFormat", "")).lower() == "cyclonedx":
        return "cyclonedx"
    spec = str(document.get("specVersion", ""))
    if spec in _CYCLONEDX_SPECS:
        return "cyclonedx"
    ctx = document.get("@context")
    ctx_text = ""
    if isinstance(ctx, str):
        ctx_text = ctx
    elif isinstance(ctx, list):
        ctx_text = " ".join(str(x) for x in ctx)
    elif isinstance(ctx, dict):
        ctx_text = " ".join(str(x) for x in ctx.values())
    if "spdx" in ctx_text.lower():
        return "spdx"
    if "@graph" in document or "spdxId" in document:
        return "spdx"
    # A bare components[] with a CycloneDX-ish metadata is still CycloneDX.
    if isinstance(document.get("components"), list) and "metadata" in document:
        return "cyclonedx"
    return None


def _component(bom_ref, kind, name, version, licenses, hashes, depends_on):
    return {
        "bom_ref": bom_ref,
        "kind": kind,
        "name": name,
        "version": version,
        "licenses": licenses,
        "hashes": hashes,
        "depends_on": depends_on,
    }


# ---------------------------------------------------------------------------
# CycloneDX
# ---------------------------------------------------------------------------

def _cdx_licenses(comp: dict) -> list:
    out: list[str] = []
    lic = comp.get("licenses")
    if not isinstance(lic, list):
        return out
    for item in lic:
        if not isinstance(item, dict):
            continue
        lo = item.get("license")
        if isinstance(lo, dict):
            val = lo.get("id") or lo.get("name")
            if isinstance(val, str) and val.strip():
                out.append(val.strip())
        elif isinstance(item.get("expression"), str) and item["expression"].strip():
            out.append(item["expression"].strip())
    return out


def _cdx_hashes(comp: dict) -> dict:
    out: dict[str, str] = {}
    hs = comp.get("hashes")
    if not isinstance(hs, list):
        return out
    for h in hs:
        if isinstance(h, dict) and isinstance(h.get("alg"), str) and isinstance(h.get("content"), str):
            out[h["alg"]] = h["content"]
    return out


def _cdx_kind(comp: dict) -> tuple[str, Optional[str]]:
    """Return (kind, raw_type_if_other)."""
    t = comp.get("type")
    if t == "machine-learning-model":
        return "model", None
    if t == _WEIGHT_DATASET_TYPE:
        data = comp.get("data")
        if isinstance(data, dict) and data.get("type") == "dataset":
            return "dataset", None
    return "other", (t if isinstance(t, str) else "<untyped>")


def _import_cyclonedx(document: dict) -> dict:
    spec = str(document.get("specVersion", ""))
    source_format = _CYCLONEDX_SPECS.get(spec, "cyclonedx-1.6")

    raw: list[dict] = []
    meta = document.get("metadata")
    if isinstance(meta, dict) and isinstance(meta.get("component"), dict):
        raw.append(meta["component"])
    comps = document.get("components")
    if isinstance(comps, list):
        raw.extend(c for c in comps if isinstance(c, dict))

    components: list[dict] = []
    ignored: dict[str, int] = {}
    by_ref: dict[str, dict] = {}
    for comp in raw:
        kind, other_type = _cdx_kind(comp)
        bom_ref = comp.get("bom-ref") if isinstance(comp.get("bom-ref"), str) else None
        name = comp.get("name") if isinstance(comp.get("name"), str) else None
        version = comp.get("version") if isinstance(comp.get("version"), str) else None
        rec = _component(bom_ref, kind, name, version,
                         _cdx_licenses(comp), _cdx_hashes(comp), [])
        components.append(rec)
        if bom_ref is not None and bom_ref not in by_ref:
            by_ref[bom_ref] = rec
        if kind == "other":
            ignored[other_type] = ignored.get(other_type, 0) + 1

    deps = document.get("dependencies")
    if isinstance(deps, list):
        for d in deps:
            if not isinstance(d, dict):
                continue
            ref = d.get("ref")
            targets = d.get("dependsOn")
            if not isinstance(ref, str) or ref not in by_ref or not isinstance(targets, list):
                continue
            edges = by_ref[ref]["depends_on"]
            for t in targets:
                if isinstance(t, str) and t not in edges:
                    edges.append(t)

    return {
        "schema_version": BOMFACTS_SCHEMA,
        "source_format": source_format,
        "components": components,
        "ignored": ignored,
        "unmapped": 0,
    }


# ---------------------------------------------------------------------------
# SPDX 3.0 AI profile (JSON-LD)
# ---------------------------------------------------------------------------

_SPDX_PACKAGE_TYPES = {"software_package", "package", "software_softwarepackage"}


def _spdx_type(el: dict) -> str:
    t = el.get("type") or el.get("@type")
    if isinstance(t, list):
        t = t[0] if t else None
    return str(t).split(":")[-1].lower() if isinstance(t, str) else ""


def _spdx_is_package(el: dict) -> bool:
    return _spdx_type(el) in _SPDX_PACKAGE_TYPES


def _spdx_licenses(el: dict) -> list:
    out: list[str] = []
    for key in ("hasConcludedLicense", "hasDeclaredLicense"):
        v = el.get(key)
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
            break  # concluded preferred; then declared
    return out


def _spdx_hashes(el: dict) -> dict:
    out: dict[str, str] = {}
    vu = el.get("verifiedUsing")
    items = vu if isinstance(vu, list) else ([vu] if isinstance(vu, dict) else [])
    for h in items:
        if not isinstance(h, dict):
            continue
        alg = h.get("algorithm")
        val = h.get("hashValue")
        if isinstance(alg, str) and isinstance(val, str):
            # SPDX algorithm names are lowercase ("sha256"); normalize to the
            # CycloneDX spelling so hashes compare across formats.
            out[_norm_alg(alg)] = val
    return out


def _norm_alg(alg: str) -> str:
    a = alg.strip().lower().replace("-", "").replace("_", "")
    table = {"sha256": "SHA-256", "sha512": "SHA-512", "sha1": "SHA-1",
             "md5": "MD5", "sha384": "SHA-384"}
    return table.get(a, alg)


def _spdx_kind(el: dict) -> str:
    """Classify an SPDX package element by its profile/type markers (B.1).

    Dataset markers win over model markers so a dataset carrying an AI-adjacent
    field is not mislabelled a model.
    """
    def _text(*keys) -> str:
        parts = []
        for k in keys:
            v = el.get(k)
            if isinstance(v, list):
                parts.extend(str(x) for x in v)
            elif v is not None:
                parts.append(str(v))
        return " ".join(parts).lower()

    marker = _text("type", "@type", "profileConformance", "primaryPurpose")
    # Dataset markers.
    if "datasetpackage" in marker or el.get("datasetType") is not None or "dataset" in marker:
        return "dataset"
    # Model / AI markers.
    if "aipackage" in marker or el.get("typeOfModel") is not None or "model" in marker:
        return "model"
    if "ai" in marker.split():
        return "model"
    return "other"


def _import_spdx(document: dict) -> dict:
    graph = document.get("@graph")
    if not isinstance(graph, list):
        # A single-element document (the element at top level).
        graph = [document] if document.get("spdxId") or document.get("@type") or document.get("type") else []

    components: list[dict] = []
    by_ref: dict[str, dict] = {}
    unmapped = 0
    pending: list[dict] = []  # relationship elements, applied after packages

    for el in graph:
        if not isinstance(el, dict):
            unmapped += 1
            continue
        etype = _spdx_type(el)
        if etype == "relationship":
            pending.append(el)
            continue
        if not _spdx_is_package(el):
            unmapped += 1
            continue
        bom_ref = el.get("spdxId") if isinstance(el.get("spdxId"), str) else None
        name = el.get("name") if isinstance(el.get("name"), str) else None
        version = el.get("versionInfo") if isinstance(el.get("versionInfo"), str) else None
        rec = _component(bom_ref, _spdx_kind(el), name, version,
                         _spdx_licenses(el), _spdx_hashes(el), [])
        # hasDownloadLocation -> externalReference-ish is not part of the facts
        # shape (B.1 keeps the four edge-relevant fields); download location does
        # not affect any decidable check, so it is dropped deliberately.
        components.append(rec)
        if bom_ref is not None and bom_ref not in by_ref:
            by_ref[bom_ref] = rec

    for rel in pending:
        rtype = str(rel.get("relationshipType", "")).split(":")[-1]
        if rtype != "dependsOn":
            continue
        frm = rel.get("from") or rel.get("element")
        to = rel.get("to")
        if not isinstance(frm, str) or frm not in by_ref:
            continue
        targets = to if isinstance(to, list) else ([to] if isinstance(to, str) else [])
        edges = by_ref[frm]["depends_on"]
        for t in targets:
            if isinstance(t, str) and t not in edges:
                edges.append(t)

    return {
        "schema_version": BOMFACTS_SCHEMA,
        "source_format": "spdx-3.0-ai",
        "components": components,
        "ignored": {},
        "unmapped": unmapped,
    }


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def import_bom(document: Any) -> dict:
    """Import a BOM document into ``bomfacts/1``. Raises ``ValueError`` if the
    format is unrecognized (never guesses)."""
    fmt = detect_format(document)
    if fmt == "cyclonedx":
        return _import_cyclonedx(document)
    if fmt == "spdx":
        return _import_spdx(document)
    raise ValueError("unrecognized BOM document format (not CycloneDX or SPDX 3.0 AI)")
