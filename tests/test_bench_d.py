"""Part A-D bench: regeneration byte-identical, marker discipline, GATE E1 (§E1.7/§E1.9)."""
from releaseseal import BENCH_MANIFEST_D_SCHEMA, DSAMPLE_SEED
from releaseseal.bench import gate_e1, generate_d, score_d
from releaseseal.canonical import canonical_bytes, canonical_sha256

CLASSES = ("W1", "W2", "W3", "W4", "W5", "W6", "W7")


def test_regeneration_byte_identical():
    a = generate_d(seed=DSAMPLE_SEED)
    b = generate_d(seed=DSAMPLE_SEED)
    assert canonical_bytes(a) == canonical_bytes(b)
    assert a["cases_sha256"] == b["cases_sha256"] == canonical_sha256(a["cases"])


def test_different_seed_differs():
    assert generate_d(seed=1)["cases_sha256"] != generate_d(seed=2)["cases_sha256"]


def test_manifest_schema_and_composition():
    m = generate_d(seed=DSAMPLE_SEED)
    assert m["schema_version"] == BENCH_MANIFEST_D_SCHEMA
    assert len(m["cases"]) == 120
    assert m["composition"] == {c: 12 for c in CLASSES} | {"clean": 36}


def test_marker_discipline():
    m = generate_d(seed=DSAMPLE_SEED)
    for case in m["cases"]:
        assert case["id"].startswith("dcase-")
        assert case["kind"] in CLASSES + ("clean",)
        for marker in case["expected"]:
            assert marker in CLASSES            # class ids only, never W8/free text/severity
        if case["kind"] == "clean":
            assert case["expected"] == []
        else:
            assert case["expected"] == [case["kind"]]
        assert case["snapshot"]["schema_version"] == "dsnapshot/1"


def test_gate_e1_passes_on_dev_split():
    m = generate_d(seed=DSAMPLE_SEED)
    scored = score_d(m)
    for cls, r in scored["recall"].items():
        assert r is not None and r >= 0.90, f"{cls} recall {r}"
    assert scored["clean_fp_rate"] <= 0.05
    assert gate_e1(scored)["pass"] is True


def test_no_w8_in_counted_scorer():
    """Info/heuristic findings (W8, contamination_measured, dedup_measured) never
    flip a clean case to a false positive."""
    m = generate_d(seed=DSAMPLE_SEED)
    scored = score_d(m)
    assert scored["clean_fp"] == 0
