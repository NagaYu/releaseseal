"""Dataset checks W1–W8: positive / negative / near-miss, masking, counting (§E1.3)."""
import json

from releaseseal.evidence import build_pack, render_report
from releaseseal.rules import load_pack
from releaseseal.snapshot.dschema import finalize, make_dcard, make_dsnapshot, make_dsource
from releaseseal.snapshot.dsample import build_sample
from releaseseal.verify import gate_counted_dataset, verify_dataset
from releaseseal.verify.wchecks import mask

_EN = ["the research corpus collects freely licensed articles about natural science and public history",
       "volunteers transcribed old community newsletters describing local gardening clubs and seasonal harvest festivals",
       "the collection gathers open recipes for soups stews and baked bread from many regions"]


def _snap(*, declarations_yaml=None, rows=None, croissant=None, files=None, splits=None,
          license_files=None):
    rows = rows if rows is not None else {"train": [{"text": t} for t in _EN]}
    yaml = {"annotations": {}}
    if declarations_yaml:
        yaml = declarations_yaml
    card = make_dcard(yaml=yaml)
    sample = build_sample(rows, seed=20261111)
    if splits is None:
        splits = [{"name": n, "num_rows": len(r), "num_bytes": None} for n, r in rows.items()]
    if files is None:
        files = [{"path": f"{n}.jsonl", "size": 10, "sha256": "a" * 64, "hash_source": "streamed"}
                 for n in rows]
    snap = make_dsnapshot(captured_at="2026-11-11",
                          source=make_dsource("local_dataset", path="/x"),
                          files=files, card=card, croissant=croissant, splits=splits, sample=sample,
                          license_files=license_files)
    return finalize(snap)


def _codes(snap):
    return {(f["check"], f["code"]) for f in verify_dataset(snap)["findings"]}


def _counted(snap):
    return {(f["check"], f["code"]) for f in gate_counted_dataset(verify_dataset(snap)["findings"])}


# --- W1 --------------------------------------------------------------------

def test_w1_croissant_inconsistency():
    snap = _snap(declarations_yaml={"license": "apache-2.0", "annotations": {}},
                 croissant={"license": "mit", "distribution": [], "recordSet": []})
    assert ("W1", "license_inconsistent") in _counted(snap)


def test_w1_unknown_license_low():
    snap = _snap(declarations_yaml={"license": "weird-custom-9.9", "annotations": {}},
                 croissant={"license": "weird-custom-9.9", "distribution": [], "recordSet": []})
    assert ("W1", "license_unknown") in _counted(snap)


def test_w1_clean_consistent_silent():
    snap = _snap(declarations_yaml={"license": "apache-2.0", "annotations": {}},
                 croissant={"license": "apache-2.0", "distribution": [], "recordSet": []})
    assert not any(c == "W1" for c, _ in _counted(snap))


# --- W1 LICENSE-file identification leg (Phase-E2, D-37) --------------------

# Synthetic LICENSE texts (headers only; enough to carry the pinned required
# phrases). Copyright/wrapped lines are exercised in the normalization test.
_LIC_APACHE = (
    "                                 Apache License\n"
    "                           Version 2.0, January 2004\n"
    "                        http://www.apache.org/licenses/\n"
)
_LIC_MIT = (
    "MIT License\n\n"
    "Copyright (c) 2026 Some Author\n\n"
    "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
    "of this software and associated documentation files (the \"Software\"), to deal\n"
    "in the Software without restriction, including without limitation the rights\n"
)
_LIC_GPL = (
    "                    GNU GENERAL PUBLIC LICENSE\n"
    "                       Version 3, 29 June 2007\n"
)
_LIC_LGPL = (
    "                   GNU LESSER GENERAL PUBLIC LICENSE\n"
    "                       Version 3, 29 June 2007\n\n"
    "  This version of the GNU Lesser General Public License incorporates the\n"
    "terms and conditions of version 3 of the GNU General Public License.\n"
)
_LIC_CC_BY = "Creative Commons Attribution 4.0 International Public License\n"
_LIC_CC_BY_NC = "Creative Commons Attribution-NonCommercial 4.0 International Public License\n"


def test_w1_license_file_matches_declared_silent():
    snap = _snap(declarations_yaml={"license": "apache-2.0", "annotations": {}},
                 license_files=[{"path": "LICENSE", "text": _LIC_APACHE}])
    assert not any(c == "W1" for c, _ in _counted(snap))


def test_w1_license_file_vs_declared_mismatch():
    # LICENSE identifies mit, card declares apache-2.0 -> inconsistent (high).
    snap = _snap(declarations_yaml={"license": "apache-2.0", "annotations": {}},
                 license_files=[{"path": "LICENSE", "text": _LIC_MIT}])
    assert ("W1", "license_inconsistent") in _counted(snap)


def test_w1_license_file_vs_croissant_mismatch():
    snap = _snap(declarations_yaml={"license": None, "annotations": {}},
                 croissant={"license": "mit", "distribution": [], "recordSet": []},
                 license_files=[{"path": "LICENSE", "text": _LIC_APACHE}])
    assert ("W1", "license_inconsistent") in _counted(snap)


def test_w1_license_file_with_copyright_and_wrapped_lines():
    # Copyright lines dropped, wrapped lines collapsed -> still identifies mit.
    wrapped = (
        "   MIT   License\n"
        "Copyright (c) 2026 A. Author\n"
        "copyright holder line that must be dropped\n"
        "Permission is hereby granted, free of charge, to any person obtaining\n"
        "a copy\n"                      # 'a copy' wraps to the next line
        "of this software, to deal\n"
        "in the Software without\n"
        "restriction, ...\n"
    )
    from releaseseal.verify.wchecks import identify_license_file, normalize_license_text
    from releaseseal.rules import load_pack
    pack = load_pack("dataset-hub-v1")
    norm = normalize_license_text(wrapped)
    assert "copyright" not in norm
    assert identify_license_file(wrapped, pack) == "mit"


def test_w1_unidentifiable_license_silent():
    snap = _snap(declarations_yaml={"license": "apache-2.0", "annotations": {}},
                 license_files=[{"path": "LICENSE", "text": "Totally bespoke terms, all rights reserved.\n"}])
    assert not any(c == "W1" for c, _ in _counted(snap))


def test_w1_identification_order_lgpl_before_gpl():
    from releaseseal.verify.wchecks import identify_license_file
    from releaseseal.rules import load_pack
    pack = load_pack("dataset-hub-v1")
    assert identify_license_file(_LIC_LGPL, pack) == "lgpl-3.0-only"
    assert identify_license_file(_LIC_GPL, pack) == "gpl-3.0-only"


def test_w1_cc_by_nc_not_confused_with_cc_by():
    from releaseseal.verify.wchecks import identify_license_file
    from releaseseal.rules import load_pack
    pack = load_pack("dataset-hub-v1")
    assert identify_license_file(_LIC_CC_BY, pack) == "cc-by-4.0"
    assert identify_license_file(_LIC_CC_BY_NC, pack) == "cc-by-nc-4.0"


def test_w1_all_nine_license_ids_identify():
    from releaseseal.verify.wchecks import identify_license_file
    from releaseseal.rules import load_pack
    pack = load_pack("dataset-hub-v1")
    ids = set(pack["license_file_order"])
    assert ids == {"apache-2.0", "mit", "bsd-3-clause", "cc-by-4.0", "cc-by-nc-4.0",
                   "cc0-1.0", "gpl-3.0-only", "lgpl-3.0-only", "mpl-2.0"}
    texts = {
        "apache-2.0": _LIC_APACHE,
        "mit": _LIC_MIT,
        "gpl-3.0-only": _LIC_GPL,
        "lgpl-3.0-only": _LIC_LGPL,
        "cc-by-4.0": _LIC_CC_BY,
        "cc-by-nc-4.0": _LIC_CC_BY_NC,
        "bsd-3-clause": (
            "Redistribution and use in source and binary forms, with or without\n"
            "modification, are permitted provided that the following conditions are met:\n"
            "3. Neither the name of the organization nor the names of its\n"
            "   contributors may be used to endorse or promote products.\n"
        ),
        "cc0-1.0": "Creative Commons Legal Code\n\nCC0 1.0 Universal\n",
        "mpl-2.0": "Mozilla Public License Version 2.0\n",
    }
    for lic_id, text in texts.items():
        assert identify_license_file(text, pack) == lic_id, lic_id


# --- W2 --------------------------------------------------------------------

def test_w2_incompatible_source():
    snap = _snap(declarations_yaml={"license": "apache-2.0",
                 "annotations": {"sources": [{"name": "nc", "license": "cc-by-nc-4.0"}]}})
    assert ("W2", "source_license_incompatible") in _counted(snap)


def test_w2_unknown_source_license_low():
    snap = _snap(declarations_yaml={"license": "apache-2.0",
                 "annotations": {"sources": [{"name": "m", "license": "mystery-1.0"}]}})
    assert ("W2", "license_unknown") in _counted(snap)


def test_w2_compatible_source_silent():
    snap = _snap(declarations_yaml={"license": "apache-2.0",
                 "annotations": {"sources": [{"name": "ok", "license": "apache-2.0"}]}})
    assert not any(c == "W2" for c, _ in _counted(snap))


# --- W3 --------------------------------------------------------------------

def test_w3_declared_file_missing():
    snap = _snap(declarations_yaml={"annotations": {"file_inventory": [{"path": "nope.jsonl", "rows": None}]}})
    assert ("W3", "declared_file_missing") in _counted(snap)


def test_w3_undeclared_data_file():
    rows = {"train": [{"text": t} for t in _EN]}
    files = [{"path": "train.jsonl", "size": 1, "sha256": "a" * 64, "hash_source": "streamed"},
             {"path": "extra.jsonl", "size": 1, "sha256": "b" * 64, "hash_source": "streamed"}]
    snap = _snap(rows=rows, files=files,
                 declarations_yaml={"annotations": {"file_inventory": [{"path": "train.jsonl", "rows": 3}]}})
    assert ("W3", "undeclared_data_file") in _counted(snap)


def test_w3_row_count_mismatch():
    snap = _snap(declarations_yaml={"annotations": {"file_inventory": [{"path": "train.jsonl", "rows": 99}]}})
    assert ("W3", "row_count_mismatch") in _counted(snap)


def test_w3_no_inventory_silent():
    snap = _snap(declarations_yaml={"annotations": {}})
    assert not any(c == "W3" for c, _ in _counted(snap))


# --- W4 + masking ----------------------------------------------------------

def test_w4_falsified_when_declared_none_and_masked():
    email = "alice.smith@example.org"
    rows = {"train": [{"text": f"please write to {email} about the english corpus today"}]}
    snap = _snap(rows=rows, declarations_yaml={"annotations": {"pii": "none"}})
    doc = verify_dataset(snap)
    w4 = [f for f in doc["findings"] if f["check"] == "W4"]
    assert w4 and w4[0]["code"] == "pii_claim_falsified" and w4[0]["severity"] == "high"
    # masking (hard rule): the full value never appears anywhere
    blob = json.dumps(doc) + render_report(build_pack(snap, doc))
    assert email not in blob
    assert "al" in w4[0]["evidence"]["actual"] and "•" in w4[0]["evidence"]["actual"]


def test_w4_present_disclosure_is_medium_not_falsification():
    """Honest pii:'present' + a detector hit -> pii_detected medium (not high)."""
    rows = {"train": [{"text": "card 4111111111111111 appears in this disclosed english record"}]}
    snap = _snap(rows=rows, declarations_yaml={"annotations": {"pii": "present"}})
    w4 = [f for f in verify_dataset(snap)["findings"] if f["check"] == "W4"]
    assert w4 and w4[0]["code"] == "pii_detected" and w4[0]["severity"] == "medium"
    assert "4111111111111111" not in json.dumps(w4)       # masked


def test_w4_clean_no_detector_silent():
    snap = _snap(declarations_yaml={"annotations": {"pii": "none"}})
    assert not any(c == "W4" for c, _ in _codes(snap))


def test_mask_helper():
    assert mask("abcdefgh") == "ab••••gh"
    assert mask("abcd") == "••••"
    assert mask("abcde") == "ab•de"


# --- W5 --------------------------------------------------------------------

def test_w5_decontamination_falsified():
    item = load_pack("contamination-v1")["suites"][0]["items"][0]
    rows = {"train": [{"text": item}]}
    snap = _snap(rows=rows, declarations_yaml={"annotations": {"decontaminated_against": ["benchsuite-alpha"]}})
    assert ("W5", "decontamination_claim_falsified") in _counted(snap)


def _load_real_suite_item(suite_id):
    import os
    fx = os.path.join(os.path.dirname(__file__), "..", "fixtures", "contamination",
                      f"{suite_id}.json")
    with open(fx, encoding="utf-8") as fh:
        return json.load(fh)["items"][0]


def test_w5_ngram_hashes_suite_measures_contamination():
    # A row carrying a real gsm8k-test question overlaps the hashed suite -> info.
    item = _load_real_suite_item("gsm8k-test")
    snap = _snap(rows={"train": [{"text": item}]})
    codes = _codes(snap)
    assert ("W5", "contamination_measured") in codes
    # Still info (never gate-counted) absent a decontamination claim.
    assert ("W5", "contamination_measured") not in _counted(snap)


def test_w5_ngram_hashes_suite_falsifies_decontamination_claim():
    item = _load_real_suite_item("squad-validation")
    snap = _snap(declarations_yaml={"annotations": {"decontaminated_against": ["squad-validation"]}},
                 rows={"train": [{"text": item}]})
    assert ("W5", "decontamination_claim_falsified") in _counted(snap)


def test_w5_ngram_hash_set_matches_builder():
    from releaseseal.verify.wchecks import ngram_hash_set, normalize_words, _ngrams
    import hashlib
    t = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi"
    direct = {hashlib.sha256(" ".join(g).encode()).hexdigest()
              for g in _ngrams(normalize_words(t), 13)}
    assert ngram_hash_set(t, 13) == direct and direct


def test_w5_undeclared_is_info_not_counted():
    item = load_pack("contamination-v1")["suites"][0]["items"][0]
    rows = {"train": [{"text": item}]}
    snap = _snap(rows=rows, declarations_yaml={"annotations": {}})  # not declared
    codes = _codes(snap)
    assert ("W5", "contamination_measured") in codes
    assert not any(c == "W5" for c, _ in _counted(snap))           # info not counted


# --- W6 --------------------------------------------------------------------

def test_w6_dedup_rate_mismatch():
    dup = "the collection gathers open recipes for soups stews and baked bread from many regions"
    rows = {"train": [{"text": dup} for _ in range(6)]}
    snap = _snap(rows=rows, declarations_yaml={"annotations": {"dedup_rate": 0.0}})
    assert ("W6", "dedup_rate_mismatch") in _counted(snap)


def test_w6_honest_within_tolerance_is_info():
    snap = _snap(declarations_yaml={"annotations": {"dedup_rate": 0.0}})
    codes = _codes(snap)
    assert ("W6", "dedup_measured") in codes
    assert not any(c == "W6" for c, _ in _counted(snap))


# --- W7 --------------------------------------------------------------------

def test_w7_declared_language_absent():
    snap = _snap(declarations_yaml={"language": ["ja"], "annotations": {}})  # rows are en
    assert ("W7", "declared_language_absent") in _counted(snap)


def test_w7_share_mismatch():
    snap = _snap(declarations_yaml={"language": ["en", "ja"],
                 "annotations": {"language_shares": {"en": 0.5, "ja": 0.5}}})  # rows 100% en
    assert ("W7", "language_share_mismatch") in _counted(snap)


def test_w7_clean_present_silent():
    snap = _snap(declarations_yaml={"language": ["en"], "annotations": {}})
    assert not any(c == "W7" for c, _ in _counted(snap))


# --- W8 --------------------------------------------------------------------

def test_w8_signal_only_never_counted():
    snap = _snap(declarations_yaml={"annotations": {}})  # most fields absent
    w8 = [f for f in verify_dataset(snap)["findings"] if f["check"] == "W8"]
    assert w8 and all(f["heuristic"] and f["severity"] == "info" for f in w8)
    assert not any(c == "W8" for c, _ in _counted(snap))
