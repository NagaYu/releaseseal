"""Evidence pack pack/2 for datasets + pack/1 model regression (§E1.6; D-35)."""
from releaseseal import PACK_SCHEMA, PACK_SCHEMA_2
from releaseseal.bench import generate as generate_model
from releaseseal.bench import generate_d
from releaseseal.canonical import canonical_bytes
from releaseseal.evidence import build_pack, render_report, verify_pack
from releaseseal.verify import verify


def _dataset_case():
    m = generate_d(seed=20261111)
    # a W1 case so the pack carries at least one finding
    return next(c for c in m["cases"] if c["kind"] == "W1")["snapshot"]


def test_dataset_pack_is_pack2_with_kind():
    snap = _dataset_case()
    pack = build_pack(snap, verify(snap))
    assert pack["schema_version"] == PACK_SCHEMA_2
    snap_ref = next(r for r in pack["records"] if r["type"] == "snapshot_ref")
    assert snap_ref["snapshot_kind"] == "dataset"
    assert next(r for r in pack["records"] if r["type"] == "header")["pack_schema"] == PACK_SCHEMA_2


def test_dataset_pack_round_trip_and_tamper():
    snap = _dataset_case()
    pack = build_pack(snap, verify(snap))
    assert verify_pack(pack, snap)["ok"] is True
    pack["records"][-1]["finding"]["severity"] = "low"  # tamper
    assert verify_pack(pack, snap)["ok"] is False


def test_dataset_report_has_absence_caveat():
    snap = _dataset_case()
    report = render_report(build_pack(snap, verify(snap)))
    assert "does not certify" in report.lower() or "never that the corpus" in report.lower()
    assert "not a certificate" in report.lower()


def test_model_pack_still_pack1_byte_for_byte():
    """A model snapshot keeps the pack/1 code path byte-for-byte (D-35):
    no snapshot_kind, pack_schema pack/1, and stable canonical bytes."""
    m = generate_model(seed=0)
    snap = next(c for c in m["cases"] if c["kind"] == "V3")["snapshot"]
    pack = build_pack(snap, verify(snap), created_at="2026-11-11")
    assert pack["schema_version"] == PACK_SCHEMA
    snap_ref = next(r for r in pack["records"] if r["type"] == "snapshot_ref")
    assert "snapshot_kind" not in snap_ref
    header = next(r for r in pack["records"] if r["type"] == "header")
    assert header["pack_schema"] == PACK_SCHEMA
    # deterministic & verifiable
    pack2 = build_pack(snap, verify(snap), created_at="2026-11-11")
    assert canonical_bytes(pack) == canonical_bytes(pack2)
    assert verify_pack(pack, snap)["ok"] is True


def test_verify_pack_accepts_both_schemas():
    # dataset pack/2
    dsnap = _dataset_case()
    assert verify_pack(build_pack(dsnap, verify(dsnap)))["ok"] is True
    # model pack/1
    msnap = next(c for c in generate_model(seed=0)["cases"] if c["kind"] == "clean")["snapshot"]
    assert verify_pack(build_pack(msnap, verify(msnap)))["ok"] is True
