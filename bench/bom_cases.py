"""Module B mini-bench — 24 planted-defect AIBOM cases (SPEC.md B.4).

Dev-only regression suite (NOT a gate): each case is a BOM document + an optional
artifact set with a planted decidable defect (or clean). Marker discipline mirrors
§6/§E1.7 — ``expected`` is a subset of ``{"B1"}`` for defect cases, ``[]`` for
clean. Fully deterministic: ``build_cases()`` -> byte-identical manifest (tested).

Run as a smoke path:  ``python bench/bom_cases.py``  (prints the exact-match score).
"""
from __future__ import annotations

import hashlib
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from releaseseal.bom import import_bom, verify_bom  # noqa: E402
from releaseseal.canonical import canonical_sha256  # noqa: E402

BOM_MANIFEST_SCHEMA = "bom-manifest/1"


def _h(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Document builders (minimal but valid shapes)
# ---------------------------------------------------------------------------

def _cdx(components, *, metadata_component=None, dependencies=None, spec="1.6"):
    doc = {"bomFormat": "CycloneDX", "specVersion": spec,
           "metadata": {"component": metadata_component} if metadata_component else {},
           "components": components}
    if dependencies is not None:
        doc["dependencies"] = dependencies
    return doc


def _file_comp(path, sha):
    return {"bom-ref": path, "type": "file", "name": path,
            "hashes": [{"alg": "SHA-256", "content": sha}]}


def _model_comp(ref, name, *, license_=None):
    c = {"bom-ref": ref, "type": "machine-learning-model", "name": name, "version": "v1"}
    if license_:
        c["licenses"] = [{"license": {"id": license_}}]
    return c


# ---------------------------------------------------------------------------
# Case groups
# ---------------------------------------------------------------------------

def _hash_mismatch_cases():
    cases = []
    for i in range(4):
        path = f"model-{i}.safetensors"
        doc_sha = _h(f"doc-{i}")
        art_sha = _h(f"art-{i}")  # differs from doc_sha
        doc = _cdx([_file_comp(path, doc_sha)],
                   metadata_component=_model_comp(f"org/m{i}", f"org/m{i}"))
        arts = {"files": [{"path": path, "sha256": art_sha}], "license": None}
        cases.append({"id": f"bcase-{len(cases):02d}", "kind": "hash_mismatch",
                      "expected": ["B1"], "format": "cyclonedx", "bom": doc, "artifacts": arts})
    return cases


def _license_mismatch_cases():
    cases = []
    declared = ["apache-2.0", "mit", "bsd-3-clause", "cc-by-4.0"]
    actual = ["mit", "apache-2.0", "mit", "gpl-3.0-only"]
    for i in range(4):
        doc = _cdx([], metadata_component=_model_comp(f"org/lic{i}", f"org/lic{i}",
                                                      license_=declared[i]))
        arts = {"files": [], "license": actual[i]}
        cases.append({"id": f"bcase-xx", "kind": "license_mismatch",
                      "expected": ["B1"], "format": "cyclonedx", "bom": doc, "artifacts": arts})
    return cases


def _dangling_ref_cases():
    cases = []
    for i in range(4):
        ref = f"org/dang{i}"
        doc = _cdx([_file_comp(f"present-{i}.bin", _h(f"p{i}"))],
                   metadata_component={**_model_comp(ref, ref),
                                       "version": "v1"},
                   dependencies=[{"ref": ref, "dependsOn": [f"present-{i}.bin", f"ghost-{i}"]}])
        # artifacts None -> hash/license become unverifiable, dangling still fires.
        cases.append({"id": "bcase-xx", "kind": "dangling_ref",
                      "expected": ["B1"], "format": "cyclonedx", "bom": doc, "artifacts": None})
    return cases


def _undeclared_artifact_cases():
    cases = []
    exts = [".bin", ".safetensors", ".parquet", ".jsonl"]
    for i in range(4):
        accounted = f"declared-{i}.safetensors"
        orphan = f"orphan-{i}{exts[i]}"
        sha = _h(f"u{i}")
        doc = _cdx([_file_comp(accounted, sha)],
                   metadata_component=_model_comp(f"org/u{i}", f"org/u{i}"))
        arts = {"files": [{"path": accounted, "sha256": sha},
                          {"path": orphan, "sha256": _h(f"orphan{i}")}], "license": None}
        cases.append({"id": "bcase-xx", "kind": "undeclared_artifact",
                      "expected": ["B1"], "format": "cyclonedx", "bom": doc, "artifacts": arts})
    return cases


def _clean_cases():
    cases = []
    for i in range(5):
        path = f"model-clean-{i}.safetensors"
        sha = _h(f"clean{i}")
        doc = _cdx([_file_comp(path, sha)],
                   metadata_component=_model_comp(f"org/clean{i}", f"org/clean{i}",
                                                  license_="apache-2.0"))
        arts = {"files": [{"path": path, "sha256": sha}], "license": "apache-2.0"}
        cases.append({"id": "bcase-xx", "kind": "clean", "expected": [],
                      "format": "cyclonedx", "bom": doc, "artifacts": arts})
    # One clean case whose claims are simply unverifiable (artifacts withheld):
    # non-empty unverifiable, zero findings, expected [].
    path = "model-clean-5.safetensors"
    doc = _cdx([_file_comp(path, _h("clean5"))],
               metadata_component=_model_comp("org/clean5", "org/clean5", license_="mit"))
    cases.append({"id": "bcase-xx", "kind": "clean_unverifiable", "expected": [],
                  "format": "cyclonedx", "bom": doc, "artifacts": None})
    return cases


def _spdx_cases():
    def spdx_doc(sha):
        return {
            "@context": "https://spdx.org/rdf/3.0.0/spdx-context.jsonld",
            "@graph": [{
                "spdxId": "spdx:pkg-model", "type": "software_Package",
                "name": "org/spdx-model", "versionInfo": "v1",
                "hasDeclaredLicense": "apache-2.0", "typeOfModel": "transformer",
                "verifiedUsing": [{"type": "Hash", "algorithm": "sha256", "hashValue": sha}],
            }],
        }
    sha = _h("spdx-clean")
    clean = {"id": "bcase-xx", "kind": "spdx_clean", "expected": [], "format": "spdx",
             "bom": spdx_doc(sha),
             "artifacts": {"files": [{"path": "org/spdx-model", "sha256": sha}],
                           "license": "apache-2.0"}}
    defect = {"id": "bcase-xx", "kind": "spdx_hash_mismatch", "expected": ["B1"], "format": "spdx",
              "bom": spdx_doc(_h("spdx-doc")),
              "artifacts": {"files": [{"path": "org/spdx-model", "sha256": _h("spdx-art")}],
                            "license": "apache-2.0"}}
    return [clean, defect]


# ---------------------------------------------------------------------------
# Manifest + scorer
# ---------------------------------------------------------------------------

def build_cases() -> dict:
    groups = (_hash_mismatch_cases() + _license_mismatch_cases()
              + _dangling_ref_cases() + _undeclared_artifact_cases()
              + _clean_cases() + _spdx_cases())
    cases = []
    composition: dict[str, int] = {}
    for n, case in enumerate(groups):
        case = dict(case)
        case["id"] = f"bcase-{n:02d}"
        cases.append(case)
        composition[case["kind"]] = composition.get(case["kind"], 0) + 1
    return {
        "schema_version": BOM_MANIFEST_SCHEMA,
        "cases_sha256": canonical_sha256(cases),
        "composition": composition,
        "cases": cases,
    }


def score(manifest: dict) -> dict:
    """Exact-match scorer: the set of B1-producing cases must equal the set with
    non-empty ``expected``; every clean case must yield zero B1 findings."""
    total = 0
    correct = 0
    details = []
    for case in manifest.get("cases", []):
        total += 1
        facts = import_bom(case["bom"])
        result = verify_bom(facts, case.get("artifacts"))
        # All Module B findings are check=B1, non-heuristic, non-info -> all count.
        fired = {f["check"] for f in result["findings"]}
        expected = set(case.get("expected", []))
        ok = (fired == expected)
        if ok:
            correct += 1
        else:
            details.append({"id": case["id"], "kind": case["kind"],
                            "expected": sorted(expected), "fired": sorted(fired)})
    return {"total": total, "correct": correct, "exact": correct == total,
            "details": details}


def main() -> int:
    manifest = build_cases()
    scored = score(manifest)
    print("ReleaseSeal Module B mini-bench")
    print(f"  cases: {len(manifest['cases'])}  cases_sha256: {manifest['cases_sha256'][:16]}...")
    print(f"  composition: {manifest['composition']}")
    print(f"  exact-match: {scored['correct']}/{scored['total']}  "
          f"({'PASS' if scored['exact'] else 'FAIL'})")
    for d in scored["details"]:
        print(f"    MISS {d}")
    return 0 if scored["exact"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
