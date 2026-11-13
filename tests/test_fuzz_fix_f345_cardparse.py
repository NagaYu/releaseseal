"""F-3/F-4/F-5 regression — cardparse subset extension (D-45).

The minimal YAML parser must read flow lists-of-maps, YAML anchors/aliases/merge
keys, inline ``#`` comments and quoted escapes identically to a conformant
parser, so declarations are never silently dropped or corrupted per field.
"""
from releaseseal.snapshot import cardparse
from releaseseal.snapshot.dschema import extract_declarations


def _yaml(body):
    y, _ = cardparse.parse_front_matter("---\n" + body + "\n---\nbody\n")
    return y


def _decl(body):
    return extract_declarations(_yaml(body))


# --- F-3: flow list-of-maps parses exactly like block style ---------------- #

def test_sources_block_equals_flow():
    block = ("license: apache-2.0\nannotations:\n  sources:\n"
             "    - name: nc\n      license: cc-by-nc-4.0")
    flow = "license: apache-2.0\nannotations:\n  sources: [{name: nc, license: cc-by-nc-4.0}]"
    db, df = _decl(block), _decl(flow)
    assert db["sources"] == [{"name": "nc", "license": "cc-by-nc-4.0"}]
    assert db == df


def test_file_inventory_block_equals_flow_rows_stay_int():
    block = "annotations:\n  file_inventory:\n    - path: train.jsonl\n      rows: 999"
    flow = "annotations:\n  file_inventory: [{path: train.jsonl, rows: 999}]"
    db, df = _decl(block), _decl(flow)
    assert db["file_inventory"] == [{"path": "train.jsonl", "rows": 999}]
    assert isinstance(df["file_inventory"][0]["rows"], int)
    assert db == df


def test_flow_list_of_two_maps():
    flow = ("annotations:\n  sources: "
            "[{name: a, license: mit}, {name: b, license: gpl-3.0-only}]")
    assert _decl(flow)["sources"] == [
        {"name": "a", "license": "mit"}, {"name": "b", "license": "gpl-3.0-only"}]


# --- F-4: anchors / aliases / merge keys ----------------------------------- #

def test_anchor_scalar_license():
    assert _decl("license: &a apache-2.0\nother: *a")["license"] == "apache-2.0"


def test_anchor_number_keeps_type_and_alias_reuses_it():
    y = _yaml("annotations:\n  dedup_rate: &d 0.9\n  copy: *d")
    assert y["annotations"]["dedup_rate"] == 0.9
    assert isinstance(y["annotations"]["dedup_rate"], float)
    assert y["annotations"]["copy"] == 0.9  # alias reuses the anchored scalar
    assert _decl("annotations:\n  dedup_rate: &d 0.9\n  copy: *d")["dedup_rate"] == 0.9


def test_merge_key_lands():
    assert _decl("defs: &base\n  pii: none\nannotations:\n  <<: *base")["pii"] == "none"


def test_merge_key_explicit_key_wins():
    body = "defs: &base\n  pii: none\nannotations:\n  <<: *base\n  pii: present"
    assert _decl(body)["pii"] == "present"


# --- F-5: inline comments and quoting -------------------------------------- #

def test_inline_comment_stripped():
    assert _decl("license: apache-2.0 # trailing comment")["license"] == "apache-2.0"


def test_glued_hash_is_content():
    # a '#' with no preceding whitespace is content, not a comment
    assert _yaml("license: a#b")["license"] == "a#b"


def test_double_quoted_escape_processed():
    assert _yaml('license: "apa\\nche"')["license"] == "apa\nche"


def test_single_quoted_doubled_quote():
    assert _yaml("license: 'it''s'")["license"] == "it's"
