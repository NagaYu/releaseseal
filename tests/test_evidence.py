import copy

from releaseseal.bench import generate
from releaseseal.evidence import build_pack, render_report, verify_pack
from releaseseal.verify import verify


def _case_pack(kind="V1"):
    m = generate(seed=0)
    case = next(c for c in m["cases"] if c["kind"] == kind)
    snap = case["snapshot"]
    doc = verify(snap)
    return snap, doc, build_pack(snap, doc)


def test_pack_verifies_clean():
    snap, _doc, pack = _case_pack("V4")
    res = verify_pack(pack, snap)
    assert res["ok"] is True
    assert res["errors"] == []
    assert res["snapshot_sha256"] == snap["snapshot_sha256"]


def test_pack_records_rule_pack_versions():
    _snap, doc, pack = _case_pack("V4")
    header = next(r for r in pack["records"] if r["type"] == "header")
    assert header["rule_packs"] == doc["rule_packs"]


def test_tamper_breaks_chain():
    snap, _doc, pack = _case_pack("V2")
    tampered = copy.deepcopy(pack)
    # alter a finding record
    fin_idx = next(i for i, r in enumerate(tampered["records"]) if r["type"] == "finding")
    tampered["records"][fin_idx]["finding"]["severity"] = "low"
    res = verify_pack(tampered)
    assert res["ok"] is False
    assert any("prev mismatch" in e or "chain_tip" in e for e in res["errors"])


def test_snapshot_mismatch_detected():
    snap, _doc, pack = _case_pack("V1")
    other = copy.deepcopy(snap)
    other["captured_at"] = "1999-01-01"
    res = verify_pack(pack, other)
    assert res["ok"] is False
    assert any("snapshot" in e for e in res["errors"])


def test_report_wording_discipline():
    snap, _doc, pack = _case_pack("V3")
    report = render_report(pack).lower()
    assert "evidence pack" in report
    assert "not a certificate" in report
    # never asserts compliance certification
    assert "certified compliant" not in report
