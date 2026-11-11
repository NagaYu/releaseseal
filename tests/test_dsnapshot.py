"""dsnapshot/1 schema + closed-vocabulary extraction (SPEC.md §E1.1; D-27)."""
import os

from releaseseal import DSNAPSHOT_SCHEMA
from releaseseal.snapshot.dschema import (
    content_hash, croissant_subset, empty_declarations, extract_declarations,
    finalize, make_dsnapshot, make_dsource, validate,
)
from releaseseal.snapshot.hf_dataset import snapshot_from_dataset_fixture
from releaseseal.snapshot.local_dataset import snapshot_from_dir

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = os.path.join(HERE, "fixtures", "hf")


def test_extract_declarations_happy():
    y = {"license": "Apache-2.0", "language": ["en", "ja"],
         "annotations": {"pii": "present", "dedup_rate": 0.1,
                         "sources": [{"name": "a", "license": "mit"}],
                         "file_inventory": [{"path": "train.jsonl", "rows": 5}],
                         "decontaminated_against": ["benchsuite-alpha"],
                         "language_shares": {"en": 0.8, "ja": 0.2}}}
    d = extract_declarations(y)
    assert d["license"] == "apache-2.0"           # lowercased
    assert d["languages"] == ["en", "ja"]
    assert d["pii"] == "present"
    assert d["dedup_rate"] == 0.1
    assert d["sources"] == [{"name": "a", "license": "mit"}]
    assert d["file_inventory"] == [{"path": "train.jsonl", "rows": 5}]
    assert d["decontaminated_against"] == ["benchsuite-alpha"]
    assert d["language_shares"] == {"en": 0.8, "ja": 0.2}


def test_extract_wrong_types_yield_empty_never_raise():
    y = {"license": 123, "language": "en",                 # scalar language -> wrapped
         "annotations": {"pii": "maybe", "dedup_rate": 5.0,  # bad enum / out of range
                         "sources": "oops", "file_inventory": [{"rows": 3}],  # no path
                         "language_shares": {"en": "lots", "ja": 0.5},
                         "decontaminated_against": [1, "benchsuite-beta", None]}}
    d = extract_declarations(y)
    assert d["license"] is None                 # wrong-typed scalar -> null
    assert d["languages"] == ["en"]             # scalar wrapped
    assert d["pii"] is None                     # invalid enum -> null
    assert d["dedup_rate"] is None              # out of [0,1] -> null
    assert d["sources"] == []                   # wrong type -> []
    assert d["file_inventory"] == []            # item lacks path -> dropped
    assert d["decontaminated_against"] == ["benchsuite-beta"]  # non-str dropped
    assert d["language_shares"] == {"ja": 0.5}  # non-numeric value dropped


def test_extract_bool_not_a_number():
    d = extract_declarations({"annotations": {"dedup_rate": True}})
    assert d["dedup_rate"] is None


def test_empty_declarations_shape():
    e = empty_declarations()
    assert set(e) == {"license", "languages", "pii", "decontaminated_against",
                      "dedup_rate", "sources", "file_inventory", "language_shares"}


def test_croissant_subset_only_reads_known_keys():
    c = croissant_subset({"license": "mit", "extra": "ignored",
                          "distribution": [{"name": "x", "contentUrl": "x", "sha256": "z", "junk": 1}],
                          "recordSet": [{"name": "r", "field": "ignored"}]})
    assert c == {"license": "mit",
                 "distribution": [{"name": "x", "contentUrl": "x", "sha256": "z"}],
                 "recordSet": [{"name": "r"}]}
    assert croissant_subset(None) is None


def test_croissant_license_url_normalized_to_spdx_id():
    # Phase-E2 (D-39): HF auto-Croissant often carries a license URL; normalize
    # to an SPDX-ish id so W1 does not manufacture format-only inconsistencies.
    assert croissant_subset({"license": "https://choosealicense.com/licenses/apache-2.0/"})["license"] == "apache-2.0"
    assert croissant_subset({"license": ["https://spdx.org/licenses/MIT.html"]})["license"] == "mit"
    assert croissant_subset({"license": "MIT"})["license"] == "mit"          # plain id lowercased
    assert croissant_subset({"license": "cc-by-sa-4.0"})["license"] == "cc-by-sa-4.0"  # unchanged


def test_validate_and_content_hash():
    snap = finalize(make_dsnapshot(captured_at="2026-11-11",
                                   source=make_dsource("local_dataset", path="/x")))
    assert snap["schema_version"] == DSNAPSHOT_SCHEMA
    assert validate(snap) == []
    assert snap["snapshot_sha256"] == content_hash(snap)
    # tamper -> hash mismatch is detected
    snap["captured_at"] = "1999-01-01"
    assert any("snapshot_sha256" in e for e in validate(snap))


def test_validate_rejects_bad_adapter():
    snap = finalize(make_dsnapshot(captured_at="x", source={"adapter": "nope"}))
    assert any("adapter" in e for e in validate(snap))


def test_hf_dataset_fixture_offline_valid():
    snap = snapshot_from_dataset_fixture(os.path.join(FX, "dataset-tiny-clean.json"),
                                         "bench/clean-dataset")
    assert validate(snap) == []
    assert snap["source"]["adapter"] == "hf_dataset"
    assert snap["source"]["revision"] == "revcleanaaaa"
    assert snap["card"]["declarations"]["license"] == "apache-2.0"
    assert snap["croissant"]["license"] == "apache-2.0"
    assert any(f["hash_source"] == "lfs" for f in snap["files"])


def test_local_dataset_adapter(tmp_path):
    (tmp_path / "train.jsonl").write_text(
        '{"text":"a clean english line about public research data"}\n'
        '{"text":"another distinct english line about gardening and history"}\n', encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "---\nlicense: mit\nlanguage:\n  - en\nannotations:\n  pii: none\n"
        "  file_inventory:\n    - path: train.jsonl\n      rows: 2\n---\n# ds\n", encoding="utf-8")
    snap = snapshot_from_dir(str(tmp_path))
    assert validate(snap) == []
    assert snap["source"]["adapter"] == "local_dataset"
    assert snap["card"]["declarations"]["license"] == "mit"
    names = [s["name"] for s in snap["splits"]]
    assert names == ["train"] and snap["splits"][0]["num_rows"] == 2
    assert len(snap["sample"]["rows"]) == 2
