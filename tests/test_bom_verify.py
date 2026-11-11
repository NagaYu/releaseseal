"""Module B — verify_bom tests (SPEC.md B.2): each check +/-, unverifiable."""
import json
import os

from releaseseal.bom import artifacts_from_snapshot, import_bom, verify_bom

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = os.path.join(HERE, "fixtures", "bom")


def _load(name):
    with open(os.path.join(FX, name), encoding="utf-8") as fh:
        return json.load(fh)


def _facts(components, ignored=None):
    return {"schema_version": "bomfacts/1", "source_format": "cyclonedx-1.6",
            "components": components, "ignored": ignored or {}, "unmapped": 0}


def _c(**kw):
    base = {"bom_ref": None, "kind": "model", "name": None, "version": None,
            "licenses": [], "hashes": {}, "depends_on": []}
    base.update(kw)
    return base


def _codes(result):
    return sorted(f["code"] for f in result["findings"])


# --- hash mismatch -----------------------------------------------------------

def test_hash_mismatch_positive():
    facts = _facts([_c(bom_ref="f", name="w.safetensors", hashes={"SHA-256": "aa"})])
    res = verify_bom(facts, {"files": [{"path": "w.safetensors", "sha256": "bb"}], "license": None})
    assert _codes(res) == ["bom_hash_mismatch"]
    assert res["findings"][0]["severity"] == "high"


def test_hash_match_negative():
    facts = _facts([_c(bom_ref="f", name="w.safetensors", hashes={"SHA-256": "aa"})])
    res = verify_bom(facts, {"files": [{"path": "w.safetensors", "sha256": "AA"}], "license": None})
    assert res["findings"] == []  # case-insensitive match
    assert res["counts"]["unverifiable"] == 0


def test_hash_match_by_basename():
    facts = _facts([_c(bom_ref="f", name="sub/dir/w.safetensors", hashes={"SHA-256": "aa"})])
    res = verify_bom(facts, {"files": [{"path": "w.safetensors", "sha256": "bb"}], "license": None})
    assert _codes(res) == ["bom_hash_mismatch"]


# --- license mismatch --------------------------------------------------------

def test_license_mismatch_positive():
    facts = _facts([_c(bom_ref="m", name="m", licenses=["apache-2.0"])])
    res = verify_bom(facts, {"files": [], "license": "mit"})
    assert _codes(res) == ["bom_license_mismatch"]
    assert res["findings"][0]["severity"] == "medium"


def test_license_match_negative_case_insensitive():
    facts = _facts([_c(bom_ref="m", name="m", licenses=["Apache-2.0"])])
    res = verify_bom(facts, {"files": [], "license": "apache-2.0"})
    assert res["findings"] == []


# --- dangling ref ------------------------------------------------------------

def test_dangling_ref_positive_pure_document():
    facts = _facts([_c(bom_ref="a", name="a", depends_on=["b", "ghost"]),
                    _c(bom_ref="b", name="b")])
    res = verify_bom(facts, None)  # no artifacts needed
    assert _codes(res) == ["bom_dangling_ref"]
    assert res["findings"][0]["subject"] == "ghost"


def test_no_dangling_when_all_refs_present():
    facts = _facts([_c(bom_ref="a", name="a", depends_on=["b"]),
                    _c(bom_ref="b", name="b")])
    assert verify_bom(facts, None)["findings"] == []


# --- undeclared artifact -----------------------------------------------------

def test_undeclared_artifact_positive():
    facts = _facts([_c(bom_ref="f", name="declared.safetensors", hashes={"SHA-256": "aa"})])
    arts = {"files": [{"path": "declared.safetensors", "sha256": "aa"},
                      {"path": "orphan.parquet", "sha256": "zz"}], "license": None}
    res = verify_bom(facts, arts)
    assert _codes(res) == ["bom_undeclared_artifact"]
    assert res["findings"][0]["subject"] == "orphan.parquet"


def test_non_weight_file_never_undeclared():
    facts = _facts([_c(bom_ref="f", name="declared.safetensors", hashes={"SHA-256": "aa"})])
    arts = {"files": [{"path": "declared.safetensors", "sha256": "aa"},
                      {"path": "README.md", "sha256": "zz"},
                      {"path": ".gitattributes", "sha256": "qq"}], "license": None}
    assert verify_bom(facts, arts)["findings"] == []


def test_component_without_hash_still_accounts_for_file():
    # A component naming the file (no hash) accounts for it -> not undeclared.
    facts = _facts([_c(bom_ref="m", name="train.jsonl")])
    arts = {"files": [{"path": "train.jsonl", "sha256": "aa"}], "license": None}
    assert verify_bom(facts, arts)["findings"] == []


# --- unverifiable accounting -------------------------------------------------

def test_unverifiable_when_no_artifacts():
    facts = _facts([_c(bom_ref="m", name="m", licenses=["mit"], hashes={"SHA-256": "aa"})])
    res = verify_bom(facts, None)
    assert res["findings"] == []
    claims = {(u["claim"]) for u in res["unverifiable"]}
    assert claims == {"hash", "license"}
    assert res["counts"]["unverifiable_by_claim"] == {"hash": 1, "license": 1}


def test_unverifiable_when_no_matching_file():
    facts = _facts([_c(bom_ref="m", name="pkg-name", hashes={"SHA-256": "aa"})])
    res = verify_bom(facts, {"files": [{"path": "other.bin", "sha256": "bb"}], "license": None})
    # no hash finding (no match), hash claim is unverifiable; other.bin undeclared
    assert "bom_hash_mismatch" not in _codes(res)
    assert {"component": "m", "claim": "hash", "reason": "no matching artifact file"} in res["unverifiable"]


def test_no_hash_claim_when_component_has_no_hashes():
    facts = _facts([_c(bom_ref="m", name="m")])
    res = verify_bom(facts, None)
    assert res["unverifiable"] == []


def test_verified_hash_not_also_unverifiable():
    facts = _facts([_c(bom_ref="f", name="w.bin", hashes={"SHA-256": "aa"})])
    res = verify_bom(facts, {"files": [{"path": "w.bin", "sha256": "aa"}], "license": None})
    assert res["findings"] == []
    assert all(u["claim"] != "hash" for u in res["unverifiable"])


# --- artifacts_from_snapshot + counts ---------------------------------------

def test_artifacts_from_model_snapshot_clean_endtoend():
    facts = import_bom(_load("cyclonedx-1.6-model.json"))
    arts = artifacts_from_snapshot(_load("artifacts-model-clean.snap.json"))
    res = verify_bom(facts, arts)
    assert res["findings"] == []
    assert res["counts"]["components"] == {"model": 1, "dataset": 0, "other": 3}
    assert res["counts"]["ignored"] == 3


def test_artifacts_from_dataset_snapshot_license_field():
    arts = artifacts_from_snapshot(_load("artifacts-dataset-clean.snap.json"))
    assert arts["license"] == "cc-by-4.0"
    assert any(f["path"] == "train.parquet" for f in arts["files"])


def test_result_is_deterministic():
    from releaseseal.canonical import canonical_bytes
    facts = import_bom(_load("cyclonedx-1.5-dataset-dangling.json"))
    a = verify_bom(facts, None)
    b = verify_bom(facts, None)
    assert canonical_bytes(a) == canonical_bytes(b)
