import json
import os

from releaseseal.cli import main
from conftest import FIXTURES


def test_cli_snapshot_verify_pack_flow(tmp_path, capsys):
    snap_p = tmp_path / "snap.json"
    rc = main(["snapshot", "--hf", "acme/tiny-undocumented",
               "--hf-fixture", os.path.join(FIXTURES, "hf", "tiny-doc-gaps.json"),
               "-o", str(snap_p)])
    assert rc == 0 and snap_p.exists()

    findings_p = tmp_path / "findings.json"
    rc = main(["verify", str(snap_p), "-o", str(findings_p)])
    assert rc == 0
    doc = json.loads(findings_p.read_text())
    assert doc["schema_version"] == "findings/1"
    assert any(f["check"] == "V4" for f in doc["findings"])

    # --ci exits 1 when findings exist
    assert main(["verify", str(snap_p), "--ci"]) == 1

    pack_p = tmp_path / "pack.json"
    report_p = tmp_path / "report.md"
    assert main(["pack", str(snap_p), "-o", str(pack_p), "--report", str(report_p)]) == 0
    assert report_p.exists()

    rc = main(["verify-pack", str(pack_p), "--snapshot", str(snap_p)])
    assert rc == 0


def test_cli_bench_roundtrip(tmp_path):
    out = tmp_path / "bench"
    assert main(["bench", "generate", "--seed", "0", "-o", str(out)]) == 0
    manifest = out / "manifest.json"
    assert manifest.exists()
    assert main(["bench", "score", "--manifest", str(manifest)]) == 0  # exit 0 == GATE 1 PASS
