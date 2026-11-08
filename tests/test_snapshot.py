import json
import os

from releaseseal.snapshot import cardparse
from releaseseal.snapshot.hf_adapter import snapshot_from_fixture
from releaseseal.snapshot.local_adapter import snapshot_from_dir
from releaseseal.snapshot.schema import content_hash, finalize, make_snapshot, make_source, validate
from conftest import FIXTURES


def test_front_matter_and_claims():
    card = (
        "---\n"
        "license: apache-2.0\n"
        "base_model:\n  - meta/Base\n"
        "base_model_relation: finetune\n"
        "tags: [a, b]\n"
        "---\n"
        "# M\n\nA 7B model with context length of 8192 tokens.\n"
    )
    y, prose = cardparse.parse_front_matter(card)
    assert y["license"] == "apache-2.0"
    assert y["base_model"] == ["meta/Base"]
    claims = cardparse.extract_claims(y, prose)
    assert claims["param_count"] == 7_000_000_000
    assert claims["context_length"] == 8192
    assert claims["base_model"] == ["meta/Base"]
    assert claims["license"] == "apache-2.0"


def test_no_front_matter():
    y, prose = cardparse.parse_front_matter("# just prose\n")
    assert y == {}
    assert "just prose" in prose


def test_schema_validate_and_hash():
    snap = make_snapshot(captured_at="2026-01-01", source=make_source("local", path="/x"))
    snap = finalize(snap)
    assert validate(snap) == []
    assert snap["snapshot_sha256"] == content_hash(snap)
    # mutating content invalidates stored hash
    snap["captured_at"] = "2026-01-02"
    assert any("snapshot_sha256" in e for e in validate(snap))


def test_local_adapter(tmp_path):
    (tmp_path / "README.md").write_text(
        "---\nlicense: mit\ntags: [text-generation]\n---\n# Demo\n\nA 1B model.\n", encoding="utf-8"
    )
    (tmp_path / "config.json").write_text(
        json.dumps({"model_type": "llama", "hidden_size": 256, "num_hidden_layers": 4,
                    "num_attention_heads": 8, "vocab_size": 32000, "intermediate_size": 768,
                    "max_position_embeddings": 2048}),
        encoding="utf-8",
    )
    (tmp_path / "tokenizer_config.json").write_text("{\"tokenizer_class\": \"X\"}", encoding="utf-8")
    snap = snapshot_from_dir(str(tmp_path))
    assert validate(snap) == []
    assert snap["source"]["adapter"] == "local"
    assert snap["card"]["claims"]["license"] == "mit"
    paths = {f["path"] for f in snap["files"]}
    assert {"README.md", "config.json", "tokenizer_config.json"} <= paths
    for f in snap["files"]:
        assert f["sha256"] and f["hash_source"] == "streamed"


def test_local_adapter_deterministic(tmp_path):
    (tmp_path / "README.md").write_text("---\nlicense: mit\n---\n# D\n", encoding="utf-8")
    a = snapshot_from_dir(str(tmp_path), captured_at="2026-01-01")
    b = snapshot_from_dir(str(tmp_path), captured_at="2026-01-01")
    assert a["snapshot_sha256"] == b["snapshot_sha256"]


def test_hf_fixture_adapter():
    path = os.path.join(FIXTURES, "hf", "tiny-clean.json")
    snap = snapshot_from_fixture(path, "acme/tiny-llama-demo")
    assert validate(snap) == []
    assert snap["source"]["adapter"] == "hf"
    assert snap["source"]["revision"] == "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
    # LFS hash carried for the weight file, no download
    wf = next(f for f in snap["files"] if f["path"] == "model.safetensors")
    assert wf["hash_source"] == "lfs" and len(wf["sha256"]) == 64
    assert snap["config"]["model_type"] == "llama"
    assert snap["card"]["claims"]["license"] == "apache-2.0"
    assert snap["model_index"]


def test_real_recorded_fixtures_build_valid_snapshots():
    """Bundles recorded live from small public repos (audit note 2) parse offline."""
    for fn, repo in [("real-tiny-gpt2", "hf-internal-testing/tiny-random-gpt2"),
                     ("real-bert-tiny", "prajjwal1/bert-tiny")]:
        path = os.path.join(FIXTURES, "hf", fn + ".json")
        snap = snapshot_from_fixture(path, repo)
        assert validate(snap) == []
        assert snap["source"]["adapter"] == "hf"
        assert snap["files"]
