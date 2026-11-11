"""Module B — importer tests (SPEC.md B.1). Both formats, from fixtures/bom/."""
import json
import os

import pytest

from releaseseal.bom import import_bom
from releaseseal.bom.facts import detect_format

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = os.path.join(HERE, "fixtures", "bom")


def _load(name):
    with open(os.path.join(FX, name), encoding="utf-8") as fh:
        return json.load(fh)


def test_cyclonedx_16_model_mapping():
    facts = import_bom(_load("cyclonedx-1.6-model.json"))
    assert facts["schema_version"] == "bomfacts/1"
    assert facts["source_format"] == "cyclonedx-1.6"
    comps = {c["name"]: c for c in facts["components"]}
    # metadata.component first, then components[] in document order.
    assert facts["components"][0]["name"] == "acme/widget-lm"
    assert comps["acme/widget-lm"]["kind"] == "model"
    assert comps["acme/widget-lm"]["licenses"] == ["apache-2.0"]
    assert comps["acme/widget-lm"]["depends_on"] == ["model.safetensors", "tokenizer.json"]
    assert comps["model.safetensors"]["kind"] == "other"
    assert comps["model.safetensors"]["hashes"]["SHA-256"]
    # a library is kind "other" AND counted in ignored
    assert comps["numpy"]["kind"] == "other"
    assert facts["ignored"] == {"file": 2, "library": 1}
    assert facts["unmapped"] == 0


def test_cyclonedx_15_dataset_and_dangling_edge_preserved():
    facts = import_bom(_load("cyclonedx-1.5-dataset-dangling.json"))
    assert facts["source_format"] == "cyclonedx-1.5"
    root = facts["components"][0]
    assert root["kind"] == "dataset"
    # the dangling target is transcribed verbatim (verify_bom decides it's dangling)
    assert "missing-shard" in root["depends_on"]


def test_cyclonedx_17_spec_detected():
    facts = import_bom(_load("cyclonedx-1.7-model.json"))
    assert facts["source_format"] == "cyclonedx-1.7"
    assert facts["components"][0]["kind"] == "model"


def test_spdx_mapping_kinds_hashes_relationships():
    facts = import_bom(_load("spdx-3.0-ai-model.json"))
    assert facts["source_format"] == "spdx-3.0-ai"
    by = {c["name"]: c for c in facts["components"]}
    assert by["acme/widget-lm"]["kind"] == "model"
    assert by["acme/widget-lm"]["version"] == "r1"
    assert by["acme/widget-lm"]["licenses"] == ["apache-2.0"]
    # SPDX lowercase "sha256" normalized to the CycloneDX spelling
    assert "SHA-256" in by["acme/widget-lm"]["hashes"]
    assert by["acme/corpus"]["kind"] == "dataset"
    # dependsOn relationship attached to the subject package
    assert by["acme/widget-lm"]["depends_on"] == ["spdx:pkg-corpus"]


def test_spdx_unmappable_element_counted_not_guessed():
    facts = import_bom(_load("spdx-3.0-ai-with-unmapped.json"))
    assert facts["unmapped"] == 1
    assert len(facts["components"]) == 1  # only the real package mapped


def test_concluded_license_wins_over_declared():
    doc = {"@context": "spdx", "@graph": [{
        "spdxId": "x", "type": "software_Package", "name": "p",
        "hasConcludedLicense": "mit", "hasDeclaredLicense": "apache-2.0",
        "typeOfModel": "t"}]}
    facts = import_bom(doc)
    assert facts["components"][0]["licenses"] == ["mit"]


def test_unknown_format_raises():
    assert detect_format({"hello": "world"}) is None
    with pytest.raises(ValueError):
        import_bom({"hello": "world"})


def test_import_is_deterministic():
    from releaseseal.canonical import canonical_bytes
    doc = _load("cyclonedx-1.6-model.json")
    assert canonical_bytes(import_bom(doc)) == canonical_bytes(import_bom(doc))
