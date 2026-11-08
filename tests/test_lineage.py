"""Recursive lineage resolution + lineage-walk metric (audit note 1)."""
import os

from releaseseal.bench import generate_ext, lineage_walk_accuracy, score
from releaseseal.snapshot.hf_adapter import MultiRepoFixtureFetcher, build_snapshot
from releaseseal.snapshot.lineage import resolve_lineage
from releaseseal.verify import gate_counted, verify
from conftest import FIXTURES


def _chain_fetcher():
    return MultiRepoFixtureFetcher.from_file(os.path.join(FIXTURES, "hf", "lineage-chain.json"))


def test_recursion_reaches_grandparent():
    snap = build_snapshot("demo/child-finetune", None, _chain_fetcher())
    lin = snap["lineage"]
    assert set(lin) == {"demo/parent-merge", "demo/grandparent-llama"}
    assert lin["demo/grandparent-llama"]["depth"] == 2
    assert lin["demo/grandparent-llama"]["license"] == "llama-3-community"


def test_grandparent_violation_detected():
    snap = build_snapshot("demo/child-finetune", None, _chain_fetcher())
    v3 = [f for f in gate_counted(verify(snap)["findings"]) if f["check"] == "V3"]
    codes = {f["code"] for f in v3}
    assert "license_incompatible" in codes  # apache not permitted by llama-3-community grandparent
    subj = {f["subject"] for f in v3 if f["code"] == "license_incompatible"}
    assert "demo/grandparent-llama" in subj


def test_depth_cap_and_cycle_guard():
    class Loop:
        def model_info(self, repo, rev):
            return {"id": repo, "cardData": {"license": "apache-2.0", "base_model": [repo]}}
        def tree(self, repo, rev):
            return []
        def file_text(self, repo, rev, path):
            return None
    # self-referential base_model must terminate (cycle guard), depth respected
    lin = resolve_lineage(Loop(), ["x/self"], depth=8)
    assert set(lin) == {"x/self"}


def test_unreachable_ancestor_is_unresolved():
    class Missing:
        def model_info(self, repo, rev):
            raise KeyError(repo)
        def tree(self, repo, rev):
            return []
        def file_text(self, repo, rev, path):
            return None
    lin = resolve_lineage(Missing(), ["gone/repo"])
    assert lin["gone/repo"]["resolved"] is False
    assert lin["gone/repo"]["license"] is None


def test_dev_ext_lineage_walk_perfect():
    m = generate_ext(seed=0)
    assert generate_ext(seed=0)["cases_sha256"] == m["cases_sha256"]  # deterministic
    sc = score(m)
    assert sc["recall"]["V3"] == 1.0
    assert sc["clean_fp_rate"] == 0.0
    lw = sc["lineage_walk"]
    assert lw["accuracy"] == 1.0 and lw["mismatches"] == []


def test_lineage_walk_none_for_plain_split():
    from releaseseal.bench import generate
    assert lineage_walk_accuracy(generate(seed=0)) is None
