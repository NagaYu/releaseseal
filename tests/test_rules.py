from releaseseal.rules import DEFAULT_PACK_IDS, load_pack, load_packs, pack_versions


def test_all_default_packs_load():
    packs = load_packs()
    assert set(packs) == set(DEFAULT_PACK_IDS)
    for pid, pack in packs.items():
        assert pack["pack_id"] == pid
        assert "version" in pack


def test_pack_versions_recorded():
    # Default profile now uses gpai-eu-v3 (D-24/D-25); v1 (1.0.0) and v2 (2.0.0)
    # are retained so the Part B v1/v2 runs reproduce.
    versions = pack_versions(load_packs())
    assert versions["license-terms-v1"] == "1.0.0"
    assert versions["gpai-eu-v3"] == "3.0.0"
    assert load_pack("gpai-eu-v1")["version"] == "1.0.0"
    assert load_pack("gpai-eu-v2")["version"] == "2.0.0"
    assert load_pack("gpai-eu-v3")["version"] == "3.0.0"


def test_license_terms_shape():
    pack = load_pack("license-terms-v1")
    licenses = pack["licenses"]
    assert "apache-2.0" in licenses and "llama-3-community" in licenses
    # a derivative may always declare the ancestor's own license
    for lic_id, entry in licenses.items():
        assert lic_id in entry["derivative_may_declare"]
    # llama-3-community does not permit a derivative to declare apache-2.0
    assert "apache-2.0" not in licenses["llama-3-community"]["derivative_may_declare"]


def test_gpai_items_have_sources():
    for pid in ("gpai-eu-v1", "gpai-eu-v2"):
        pack = load_pack(pid)
        assert pack["items"]
        for item in pack["items"]:
            assert item.get("source")
            assert item.get("profile") in pack["profiles"]


def test_authoring_item_set_in_sync_with_pack():
    # Single source of truth (D-25): docs/authoring-item-set.md is generated from
    # the active gpai pack; it must stay in sync, and cover exactly 16 items.
    import os
    from releaseseal.rules import authoring_item_set, render_authoring_item_set_md, active_gpai_pack_id
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md_path = os.path.join(here, "docs", "authoring-item-set.md")
    with open(md_path, encoding="utf-8") as fh:
        committed = fh.read()
    assert committed == render_authoring_item_set_md(), \
        "docs/authoring-item-set.md is stale; regenerate it from the pack"
    pack_ids = [i["id"] for i in load_pack(active_gpai_pack_id())["items"]]
    file_ids = [ln.split("`")[1] for ln in committed.splitlines() if ln.startswith("- `")]
    assert file_ids == pack_ids
    assert len(pack_ids) == 16


def test_gpai_v3_is_active_and_content_word():
    pack = load_pack("gpai-eu-v3")
    assert pack["version"] == "3.0.0"
    # content-word patterns present; no legacy fixed-phrase keyword lists
    assert any("patterns" in i for i in pack["items"])
    assert all("keywords" not in i for i in pack["items"])


def test_gpai_v2_provider_doc_items():
    pack = load_pack("gpai-eu-v2")
    prov = [i for i in pack["items"] if i.get("provider_doc")]
    assert {i["id"] for i in prov} == {"cop.copyright_policy", "cop.training_content_summary"}
    for i in prov:
        assert i.get("yaml_fields")  # a reference field path
        # bare generic words must not be keywords (D-22)
        assert "copyright" not in i["keywords"]
