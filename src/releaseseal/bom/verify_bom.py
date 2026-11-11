"""BOM facts + artifacts -> result (`bom-result/1`) — SPEC.md B.2.

Decidable checks only (all `finding/1`, ``check="B1"``): hash mismatch, license
mismatch, dangling bom-ref, undeclared artifact. Every claim whose evidence is not
provided is an `unverifiable` entry — first-class, counted, never a finding and
never a silent pass. Deterministic ordering.
"""
from __future__ import annotations

from typing import Any, Optional

from ..verify.findings import finding, make_evidence

BOM_RESULT_SCHEMA = "bom-result/1"

# Extensions that make a file a weight or data artifact (B.2 undeclared check).
_WEIGHT_EXTS = (".safetensors", ".bin", ".gguf", ".onnx", ".pt", ".pth",
                ".h5", ".msgpack", ".tflite", ".npz")
_DATA_EXTS = (".jsonl", ".csv", ".parquet", ".arrow", ".tfrecord")
_WEIGHT_OR_DATA = _WEIGHT_EXTS + _DATA_EXTS


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def artifacts_from_snapshot(snapshot: dict) -> dict:
    """Build an artifact set (B.2 shape) from a model or dataset snapshot.

    Files come from ``snapshot.files`` (path + sha256, null where unknown); the
    declared license from ``card.claims.license`` (model) or
    ``card.declarations.license`` (dataset).
    """
    files = []
    for f in snapshot.get("files", []) if isinstance(snapshot.get("files"), list) else []:
        if isinstance(f, dict) and isinstance(f.get("path"), str):
            sha = f.get("sha256")
            files.append({"path": f["path"], "sha256": sha if isinstance(sha, str) else None})

    license_ = None
    card = snapshot.get("card")
    if isinstance(card, dict):
        claims = card.get("claims")
        if isinstance(claims, dict) and isinstance(claims.get("license"), str):
            license_ = claims["license"]
        decl = card.get("declarations")
        if license_ is None and isinstance(decl, dict) and isinstance(decl.get("license"), str):
            license_ = decl["license"]
    return {"files": files, "license": license_}


def _match_file(name: Optional[str], files: list) -> Optional[dict]:
    """Find the artifact file for a component name: exact path, then basename."""
    if not name:
        return None
    for f in files:
        if f.get("path") == name:
            return f
    base = _basename(name)
    for f in files:
        if _basename(str(f.get("path", ""))) == base:
            return f
    return None


def verify_bom(facts: dict, artifacts: Optional[dict] = None) -> dict:
    components = facts.get("components", []) if isinstance(facts.get("components"), list) else []
    ref_set = {c.get("bom_ref") for c in components if c.get("bom_ref") is not None}

    has_artifacts = isinstance(artifacts, dict)
    art_files = artifacts.get("files", []) if has_artifacts else []
    art_files = [f for f in art_files if isinstance(f, dict) and isinstance(f.get("path"), str)]
    art_license = artifacts.get("license") if has_artifacts else None

    findings: list[dict] = []
    unverifiable: list[dict] = []
    accounted: set[str] = set()  # artifact file paths some component claimed

    for comp in components:
        ref = comp.get("bom_ref")
        label = ref or comp.get("name") or "<component>"
        name = comp.get("name")
        hashes = comp.get("hashes") or {}
        licenses = comp.get("licenses") or []

        # --- dangling refs (pure document check, always runs) ---
        for target in comp.get("depends_on") or []:
            if target not in ref_set:
                findings.append(finding(
                    "B1", "bom_dangling_ref", "medium",
                    f"Dependency edge from '{label}' names bom-ref '{target}' absent "
                    f"from the document.",
                    evidence=make_evidence(field="dependsOn", expected="a declared bom-ref",
                                           actual=target),
                    subject=target,
                ))

        # --- hash checks / unverifiable(hash) ---
        if hashes:
            match = _match_file(name, art_files) if has_artifacts else None
            if match is not None:
                accounted.add(str(match.get("path")))
                art_sha = match.get("sha256")
                compared = False
                for alg, value in sorted(hashes.items()):
                    # Compare only when the artifact carries the same alg. The
                    # artifact set models SHA-256 (snapshots record sha256).
                    if alg.upper().replace("-", "") == "SHA256" and isinstance(art_sha, str):
                        compared = True
                        if value.lower() != art_sha.lower():
                            findings.append(finding(
                                "B1", "bom_hash_mismatch", "high",
                                f"Component '{label}' hash ({alg}) disagrees with the paired "
                                f"artifact for '{match.get('path')}'.",
                                evidence=make_evidence(file=str(match.get("path")), field=alg,
                                                       expected=art_sha, actual=value),
                                subject=label,
                            ))
                if not compared:
                    unverifiable.append({"component": label, "claim": "hash",
                                         "reason": "no comparable hash in artifact set"})
            else:
                reason = ("no artifact set provided" if not has_artifacts
                          else "no matching artifact file")
                unverifiable.append({"component": label, "claim": "hash", "reason": reason})

        # --- license checks / unverifiable(license) ---
        if licenses:
            if has_artifacts and isinstance(art_license, str) and art_license.strip():
                declared = {l.strip().lower() for l in licenses if isinstance(l, str)}
                if art_license.strip().lower() not in declared:
                    findings.append(finding(
                        "B1", "bom_license_mismatch", "medium",
                        f"Component '{label}' declares license {sorted(declared)} but the "
                        f"paired snapshot declares '{art_license}'.",
                        evidence=make_evidence(field="license", expected=art_license,
                                               actual=", ".join(sorted(declared))),
                        subject=label,
                    ))
            else:
                reason = ("no artifact set provided" if not has_artifacts
                          else "no declared license in artifact set")
                unverifiable.append({"component": label, "claim": "license", "reason": reason})

    # --- undeclared artifact (requires an artifact set) ---
    if has_artifacts:
        for f in art_files:
            path = str(f.get("path"))
            if path in accounted:
                continue
            base = _basename(path).lower()
            if not base.endswith(_WEIGHT_OR_DATA):
                continue
            # Already accounted if some component matches it by name even without a
            # hash claim.
            if any(_match_file(c.get("name"), [f]) is not None for c in components):
                continue
            findings.append(finding(
                "B1", "bom_undeclared_artifact", "medium",
                f"Artifact file '{path}' is present but no BOM component accounts for it.",
                evidence=make_evidence(file=path, field="component",
                                       expected="a declaring component", actual="absent"),
                subject=path,
            ))

    findings.sort(key=lambda f: (f["code"], str(f.get("subject") or "")))
    unverifiable.sort(key=lambda u: (u["component"], u["claim"]))

    by_code: dict[str, int] = {}
    for f in findings:
        by_code[f["code"]] = by_code.get(f["code"], 0) + 1
    by_claim: dict[str, int] = {}
    for u in unverifiable:
        by_claim[u["claim"]] = by_claim.get(u["claim"], 0) + 1
    kinds = {"model": 0, "dataset": 0, "other": 0}
    for c in components:
        k = c.get("kind")
        if k in kinds:
            kinds[k] += 1

    return {
        "schema_version": BOM_RESULT_SCHEMA,
        "source_format": facts.get("source_format"),
        "findings": findings,
        "unverifiable": unverifiable,
        "counts": {
            "findings": len(findings),
            "by_code": by_code,
            "unverifiable": len(unverifiable),
            "unverifiable_by_claim": by_claim,
            "components": kinds,
            "ignored": sum(facts.get("ignored", {}).values()) if isinstance(facts.get("ignored"), dict) else 0,
            "unmapped": facts.get("unmapped", 0),
        },
    }
