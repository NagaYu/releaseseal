"""CLI smoke for the dataset commands (§E1.8)."""
import json
import os

from releaseseal.cli import main

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = os.path.join(HERE, "fixtures", "hf")


def test_dsnapshot_local_then_verify_and_pack(tmp_path):
    ds = tmp_path / "ds"
    ds.mkdir()
    (ds / "train.jsonl").write_text(
        '{"text":"a clean english sentence about public research corpora and data"}\n', encoding="utf-8")
    (ds / "README.md").write_text("---\nlicense: apache-2.0\n---\n# ds\n", encoding="utf-8")
    snap_p = tmp_path / "snap.json"
    assert main(["dsnapshot", "--local", str(ds), "-o", str(snap_p)]) == 0
    snap = json.loads(snap_p.read_text())
    assert snap["schema_version"] == "dsnapshot/1"

    assert main(["verify", str(snap_p), "-o", str(tmp_path / "f.json")]) == 0
    assert main(["pack", str(snap_p), "-o", str(tmp_path / "p.json"),
                 "--report", str(tmp_path / "r.md")]) == 0
    pack = json.loads((tmp_path / "p.json").read_text())
    assert pack["schema_version"] == "pack/2"
    assert main(["verify-pack", str(tmp_path / "p.json"), "--snapshot", str(snap_p)]) == 0


def test_dsnapshot_hf_fixture(tmp_path):
    out = tmp_path / "snap.json"
    rc = main(["dsnapshot", "--hf-dataset", "bench/clean-dataset",
               "--hf-dataset-fixture", os.path.join(FX, "dataset-tiny-clean.json"), "-o", str(out)])
    assert rc == 0
    assert json.loads(out.read_text())["source"]["adapter"] == "hf_dataset"


def test_bench_d_generate_and_score(tmp_path):
    out = tmp_path / "bd"
    assert main(["bench-d", "generate", "-o", str(out)]) == 0
    assert main(["bench-d", "score", "--manifest", str(out / "manifest.json")]) == 0  # PASS -> 0
