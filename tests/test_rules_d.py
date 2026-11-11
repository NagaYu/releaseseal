"""Generated dataset packs: byte-identical regeneration + LID behaviour (§E1.4/§E1.5)."""
import os

from releaseseal.canonical import canonical_bytes
from releaseseal.rules import load_pack
from releaseseal.rules import build_packs as bp
from releaseseal.verify import lid

PACKS = os.path.join(os.path.dirname(bp.__file__), "packs")


def _disk(pack_id):
    with open(os.path.join(PACKS, f"{pack_id}.json"), "r", encoding="utf-8") as fh:
        return fh.read()


def test_contamination_pack_regenerates_byte_identical():
    assert _disk("contamination-v1") == bp.serialize(bp.build_contamination_pack())


def test_lid_pack_regenerates_byte_identical():
    assert _disk("lid-v1") == bp.serialize(bp.build_lid_pack())


def test_contamination_pack_shape():
    from releaseseal.canonical import canonical_sha256
    pack = load_pack("contamination-v1")
    assert pack["version"] == "1.1.0"  # Phase-E2: real ngram-hash suites (D-38)
    by_id = {s["suite_id"]: s for s in pack["suites"]}
    # Synthetic suites unchanged (still plain "items", no kind key).
    for sid in ("benchsuite-alpha", "benchsuite-beta"):
        s = by_id[sid]
        assert "kind" not in s
        assert len(s["items"]) == 40 and len(set(s["items"])) == 40
        assert s["items_sha256"] == canonical_sha256(s["items"])
    # Real suites stored as ngram-hashes only — never raw benchmark text.
    for sid in ("gsm8k-test", "squad-validation"):
        s = by_id[sid]
        assert s["kind"] == "ngram-hashes"
        assert "items" not in s and "text" not in s
        assert s["ngram_count"] == len(s["ngram_hashes"]) > 0
        assert s["ngram_hashes"] == sorted(s["ngram_hashes"])  # stable order
        assert s["ngram_hashes_sha256"] == canonical_sha256(s["ngram_hashes"])
        assert len(s["source_revision"]) >= 7 and s["source_repo"]
        assert all(len(h) == 64 for h in s["ngram_hashes"])


def test_dataset_hub_pack_loads():
    pack = load_pack("dataset-hub-v1")
    assert pack["version"] == "1.1.0"  # Phase-E2: W1 LICENSE-file leg data (D-37)
    assert any(f["field"] == "license" for f in pack["fields"])
    # W1 file-leg identification data present and self-consistent.
    order = pack["license_file_order"]
    phrases = pack["license_file_phrases"]
    assert set(order) == set(phrases)
    assert set(order) == {"apache-2.0", "mit", "bsd-3-clause", "cc-by-4.0", "cc-by-nc-4.0",
                          "cc0-1.0", "gpl-3.0-only", "lgpl-3.0-only", "mpl-2.0"}
    for spec in phrases.values():
        assert spec["required"]  # at least one required phrase each
        assert isinstance(spec.get("forbidden", []), list)


def test_lid_classifier_separates_languages():
    pack = load_pack("lid-v1")
    samples = {
        "en": "the small language model was trained on public web text and books",
        "es": "el modelo de lenguaje fue entrenado con textos públicos de la web",
        "fr": "le modèle de langage a été entraîné sur des textes publics du web",
        "de": "das kleine sprachmodell wurde mit öffentlichen webtexten trainiert und bewertet",
        "ja": "この小さな言語モデルは公開されたウェブテキストで学習されました",
        "zh": "这个小型语言模型是在公开的网络文本上训练的",
    }
    for code, text in samples.items():
        assert lid.classify(text, pack) == code


def test_lid_classify_deterministic_and_und_on_short():
    pack = load_pack("lid-v1")
    t = "the collection gathers open recipes for soups and bread"
    assert lid.classify(t, pack) == lid.classify(t, pack)
    assert lid.classify("ok", pack) == "und"
    assert lid.classify("", pack) == "und"


def test_lid_load_matches_build():
    assert canonical_bytes(load_pack("lid-v1")) == canonical_bytes(bp.build_lid_pack())
