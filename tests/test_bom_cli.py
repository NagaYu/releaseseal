"""Module B — CLI smoke (SPEC.md B.5)."""
import json
import os

from releaseseal.cli import main

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = os.path.join(HERE, "fixtures", "bom")


def test_bom_import_with_artifacts(tmp_path):
    out = tmp_path / "result.json"
    rc = main(["bom", "import", os.path.join(FX, "cyclonedx-1.7-model.json"),
               "--artifacts", os.path.join(FX, "artifacts-model-hashmismatch.snap.json"),
               "-o", str(out)])
    assert rc == 0
    result = json.loads(out.read_text())
    assert result["schema_version"] == "bom-result/1"
    assert any(f["code"] == "bom_hash_mismatch" for f in result["findings"])


def test_bom_import_ci_exit_code(tmp_path):
    out = tmp_path / "result.json"
    rc = main(["bom", "import", os.path.join(FX, "cyclonedx-1.5-dataset-dangling.json"),
               "-o", str(out), "--ci"])
    assert rc == 1  # dangling ref fires even with no artifacts


def test_bom_import_without_artifacts_only_dangling(tmp_path):
    out = tmp_path / "result.json"
    rc = main(["bom", "import", os.path.join(FX, "cyclonedx-1.6-model.json"), "-o", str(out)])
    assert rc == 0
    result = json.loads(out.read_text())
    assert result["findings"] == []
    assert result["counts"]["unverifiable"] > 0  # hash/license claims unverifiable


def test_bom_unknown_format_exit_2(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"nope": true}', encoding="utf-8")
    assert main(["bom", "import", str(bad), "-o", str(tmp_path / "r.json")]) == 2


def test_bom_export_then_reimport(tmp_path):
    # Build a model pack via the CLI, then export + import.
    rel = tmp_path / "rel"
    rel.mkdir()
    (rel / "README.md").write_text("---\nlicense: mit\n---\n# m\n", encoding="utf-8")
    (rel / "model.safetensors").write_bytes(b"abc")
    snap = tmp_path / "snap.json"
    assert main(["snapshot", "--local", str(rel), "-o", str(snap)]) == 0
    pack = tmp_path / "pack.json"
    assert main(["pack", str(snap), "-o", str(pack)]) == 0
    bom = tmp_path / "bom.json"
    assert main(["bom", "export", str(pack), "--snapshot", str(snap), "-o", str(bom)]) == 0
    doc = json.loads(bom.read_text())
    assert doc["bomFormat"] == "CycloneDX"
    # re-import recovers the release + file components
    result = tmp_path / "result.json"
    assert main(["bom", "import", str(bom), "-o", str(result)]) == 0
    r = json.loads(result.read_text())
    assert r["counts"]["components"]["model"] == 1


def test_bom_export_output_byte_identical(tmp_path):
    rel = tmp_path / "rel"
    rel.mkdir()
    (rel / "README.md").write_text("---\nlicense: mit\n---\n# m\n", encoding="utf-8")
    (rel / "model.safetensors").write_bytes(b"abc")
    snap = tmp_path / "snap.json"
    main(["snapshot", "--local", str(rel), "-o", str(snap)])
    pack = tmp_path / "pack.json"
    main(["pack", str(snap), "-o", str(pack)])
    b1 = tmp_path / "b1.json"
    b2 = tmp_path / "b2.json"
    main(["bom", "export", str(pack), "--snapshot", str(snap), "-o", str(b1)])
    main(["bom", "export", str(pack), "--snapshot", str(snap), "-o", str(b2)])
    assert b1.read_bytes() == b2.read_bytes()
