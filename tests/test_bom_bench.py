"""Module B — mini-bench tests (SPEC.md B.4). Exact-match + determinism."""
import importlib.util
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("bom_cases", os.path.join(_ROOT, "bench", "bom_cases.py"))
bom_cases = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bom_cases)


def test_bench_has_24_cases_with_pinned_composition():
    manifest = bom_cases.build_cases()
    assert manifest["schema_version"] == "bom-manifest/1"
    assert len(manifest["cases"]) == 24
    comp = manifest["composition"]
    assert comp["hash_mismatch"] == 4
    assert comp["license_mismatch"] == 4
    assert comp["dangling_ref"] == 4
    assert comp["undeclared_artifact"] == 4
    assert comp["clean"] + comp["clean_unverifiable"] == 6
    assert comp["spdx_clean"] + comp["spdx_hash_mismatch"] == 2


def test_markers_are_class_ids_only():
    for case in bom_cases.build_cases()["cases"]:
        assert set(case["expected"]) <= {"B1"}
        if case["kind"].startswith("clean") or case["kind"] == "spdx_clean":
            assert case["expected"] == []
        else:
            assert case["expected"] == ["B1"]


def test_bench_scorer_exact_match():
    manifest = bom_cases.build_cases()
    scored = bom_cases.score(manifest)
    assert scored["exact"], scored["details"]
    assert scored["correct"] == 24


def test_one_clean_case_has_nonempty_unverifiable():
    from releaseseal.bom import import_bom, verify_bom
    manifest = bom_cases.build_cases()
    unv = [c for c in manifest["cases"] if c["kind"] == "clean_unverifiable"]
    assert len(unv) == 1
    res = verify_bom(import_bom(unv[0]["bom"]), unv[0]["artifacts"])
    assert res["findings"] == []
    assert res["unverifiable"]  # non-empty


def test_bench_regeneration_byte_identical():
    from releaseseal.canonical import canonical_bytes
    assert canonical_bytes(bom_cases.build_cases()) == canonical_bytes(bom_cases.build_cases())
    # cases_sha256 is over the ordered serialized cases
    m = bom_cases.build_cases()
    from releaseseal.canonical import canonical_sha256
    assert m["cases_sha256"] == canonical_sha256(m["cases"])
