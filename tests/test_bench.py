from releaseseal import BENCH_MANIFEST_SCHEMA
from releaseseal.bench import gate1, generate, score
from releaseseal.canonical import canonical_bytes, canonical_sha256


def test_generation_deterministic_bytes():
    a = generate(seed=3)
    b = generate(seed=3)
    assert canonical_bytes(a) == canonical_bytes(b)
    assert a["cases_sha256"] == b["cases_sha256"]


def test_different_seed_differs():
    assert generate(seed=1)["cases_sha256"] != generate(seed=2)["cases_sha256"]


def test_manifest_schema_and_composition():
    m = generate(seed=0)
    assert m["schema_version"] == BENCH_MANIFEST_SCHEMA
    assert len(m["cases"]) == 120
    assert m["composition"] == {"V1": 12, "V2": 12, "V3": 12, "V4": 12,
                                "V5": 12, "V6": 12, "V7": 12, "clean": 36}
    # cases_sha256 is a hash over the ordered cases
    assert m["cases_sha256"] == canonical_sha256(m["cases"])


def test_case_schema_strict_markers():
    m = generate(seed=0)
    for case in m["cases"]:
        assert isinstance(case["id"], str)
        assert case["kind"] in ("V1", "V2", "V3", "V4", "V5", "V6", "V7", "clean")
        assert isinstance(case["expected"], list)
        # markers are the short class ids only (or empty for clean)
        for marker in case["expected"]:
            assert marker in ("V1", "V2", "V3", "V4", "V5", "V6", "V7")
        if case["kind"] == "clean":
            assert case["expected"] == []
        else:
            assert case["expected"] == [case["kind"]]
        assert case["snapshot"]["schema_version"] == "snapshot/1"


def test_gate1_passes_on_dev_split():
    m = generate(seed=0)
    scored = score(m)
    for cls, r in scored["recall"].items():
        assert r is not None and r >= 0.90, f"{cls} recall {r}"
    assert scored["clean_fp_rate"] <= 0.05
    assert gate1(scored)["pass"] is True


def test_gate1_multiple_seeds():
    for s in (0, 1, 2, 7, 42):
        assert gate1(score(generate(seed=s)))["pass"] is True
