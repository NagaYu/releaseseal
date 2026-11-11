"""Module B — export + round-trip tests (SPEC.md B.3)."""
import json
import os

from releaseseal.bom import export_bom, import_bom
from releaseseal.canonical import canonical_bytes
from releaseseal.evidence import build_pack
from releaseseal.snapshot.local_adapter import snapshot_from_dir
from releaseseal.snapshot.dschema import finalize as dfinalize, make_dcard, make_dsnapshot, make_dsource
from releaseseal.verify import verify

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = os.path.join(HERE, "fixtures", "bom")


def _model_pack(tmp_path):
    d = tmp_path / "rel"
    d.mkdir()
    (d / "README.md").write_text("---\nlicense: apache-2.0\n---\n# m\n", encoding="utf-8")
    (d / "config.json").write_text('{"model_type":"gpt2"}', encoding="utf-8")
    (d / "model.safetensors").write_bytes(b"weight-bytes-here")
    snap = snapshot_from_dir(str(d))
    return build_pack(snap, verify(snap)), snap


def _dataset_pack():
    yaml = {"license": "cc-by-4.0", "language": ["en"]}
    snap = dfinalize(make_dsnapshot(
        captured_at="2026-11-11",
        source=make_dsource("local_dataset", repo_id="acme/corpus", revision="v2", path="/x"),
        files=[{"path": "train.jsonl", "size": 10,
                "sha256": "a" * 64, "hash_source": "streamed"}],
        card=make_dcard(yaml=yaml),
    ))
    return build_pack(snap, verify(snap)), snap


def _cset(facts):
    return sorted((c["name"], c["kind"], tuple(sorted(c["hashes"].items())))
                  for c in facts["components"])


def test_export_model_pack_shape(tmp_path):
    pack, snap = _model_pack(tmp_path)
    doc = export_bom(pack, snap)
    assert doc["bomFormat"] == "CycloneDX"
    assert doc["specVersion"] == "1.6"
    release = doc["metadata"]["component"]
    assert release["type"] == "machine-learning-model"
    assert release["licenses"] == [{"license": {"id": "apache-2.0"}}]
    # file components only where a hash is known (path-sorted)
    names = [c["name"] for c in doc["components"]]
    assert names == sorted(names)
    assert "model.safetensors" in names
    # snapshot digest is a property, never a component hash
    props = {p["name"]: p["value"] for p in release["properties"]}
    assert "releaseseal:snapshot_sha256" in props
    assert props["releaseseal:snapshot_sha256"] == snap["snapshot_sha256"]


def test_export_findings_summary_in_properties(tmp_path):
    pack, snap = _model_pack(tmp_path)
    doc = export_bom(pack, snap)
    props = {p["name"]: p["value"] for p in doc["metadata"]["component"]["properties"]}
    n_findings = sum(1 for r in pack["records"] if r.get("type") == "finding")
    assert props["releaseseal:finding_count"] == str(n_findings)
    # per-check counts present and stringified
    assert any(k.startswith("releaseseal:findings:") for k in props)
    assert props["releaseseal:chain_tip"] == pack["chain_tip"]


def test_roundtrip_component_set(tmp_path):
    pack, snap = _model_pack(tmp_path)
    facts = import_bom(export_bom(pack, snap))
    # release + each hashed file; release is model, files are "other"
    cset = _cset(facts)
    model_sha = next(f["sha256"] for f in snap["files"] if f["path"] == "model.safetensors")
    assert ("model.safetensors", "other", (("SHA-256", model_sha),)) in cset
    # exactly one model-kind component (the release)
    assert sum(1 for _, kind, _ in cset if kind == "model") == 1
    # idempotent
    assert _cset(import_bom(export_bom(pack, snap))) == cset


def test_export_dataset_pack_kind():
    pack, snap = _dataset_pack()
    assert pack["schema_version"] == "pack/2"
    doc = export_bom(pack, snap)
    release = doc["metadata"]["component"]
    assert release["type"] == "data"
    assert release["data"] == {"type": "dataset"}
    facts = import_bom(doc)
    assert facts["components"][0]["kind"] == "dataset"


def test_export_pack_only_no_snapshot(tmp_path):
    pack, _ = _model_pack(tmp_path)
    doc = export_bom(pack)  # no snapshot -> release only, no file components
    assert doc["components"] == []
    release = doc["metadata"]["component"]
    assert release["type"] == "machine-learning-model"
    # round-trips to just the release component
    facts = import_bom(doc)
    assert [c["kind"] for c in facts["components"]] == ["model"]


def test_export_is_deterministic(tmp_path):
    pack, snap = _model_pack(tmp_path)
    assert canonical_bytes(export_bom(pack, snap)) == canonical_bytes(export_bom(pack, snap))
