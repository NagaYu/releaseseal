import pytest

from releaseseal.bench import generate
from releaseseal.verify import Context, gate_counted, verify
from releaseseal.verify.checks import Context as Ctx, v8_undeclared_derivation
from releaseseal.verify.fingerprint import fingerprint
from releaseseal.verify.paramest import estimate_params

CLASSES = ("V1", "V2", "V3", "V4", "V5", "V6", "V7")


@pytest.fixture(scope="module")
def manifest():
    return generate(seed=0)


@pytest.mark.parametrize("cls", CLASSES)
def test_positive_each_class_fires(cls, manifest):
    """Every planted case of a class produces >=1 finding of that class."""
    cases = [c for c in manifest["cases"] if c["kind"] == cls]
    assert cases
    for case in cases:
        fired = {f["check"] for f in gate_counted(verify(case["snapshot"])["findings"])}
        assert cls in fired, f"{case['id']} ({cls}) did not fire; fired={fired}"


def test_negative_clean_cases_silent(manifest):
    """No clean case produces any gate-counted (V1-V7) finding."""
    for case in manifest["cases"]:
        if case["kind"] != "clean":
            continue
        fired = gate_counted(verify(case["snapshot"])["findings"])
        assert fired == [], f"{case['id']} clean but fired {[f['check'] for f in fired]}"


def test_param_estimate_reasonable():
    # ~1.1B-ish small config; estimate within an order of magnitude of a hand calc
    cfg = {"model_type": "llama", "hidden_size": 2048, "num_hidden_layers": 24,
           "num_attention_heads": 16, "num_key_value_heads": 16, "vocab_size": 32000,
           "intermediate_size": 5632, "tie_word_embeddings": False}
    est = estimate_params(cfg)
    assert 1_000_000_000 < est < 1_600_000_000


def test_param_estimate_none_on_missing():
    assert estimate_params({"model_type": "llama"}) is None
    assert estimate_params(None) is None


def test_v8_signal_only_and_heuristic():
    cfg = {"model_type": "llama", "hidden_size": 999, "num_hidden_layers": 7,
           "num_attention_heads": 9, "num_key_value_heads": 3, "vocab_size": 55555,
           "intermediate_size": 2997}
    fp = fingerprint(cfg)
    packs = {"fingerprints-v1": {"fields": list(__import__(
        "releaseseal.verify.fingerprint", fromlist=["DEFAULT_FIELDS"]).DEFAULT_FIELDS),
        "known_bases": {fp: "known/base-x"}}}
    ctx = Ctx(packs=packs)
    snap = {"config": cfg, "card": {"claims": {"base_model": []}}}
    found = v8_undeclared_derivation(snap, ctx)
    assert len(found) == 1
    assert found[0]["check"] == "V8" and found[0]["heuristic"] is True
    assert found[0]["severity"] == "info"
    # excluded from gate rollup
    assert gate_counted(found) == []
    # negative: a declared base_model suppresses the signal
    snap2 = {"config": cfg, "card": {"claims": {"base_model": ["known/base-x"]}}}
    assert v8_undeclared_derivation(snap2, ctx) == []


def test_v8_fires_on_real_config_with_shipped_pack():
    """known_bases is seeded (audit note 4): a derivative reusing a known base's
    architecture with no declared base_model triggers the V8 signal offline."""
    import os
    from releaseseal.snapshot.hf_adapter import snapshot_from_fixture
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    snap = snapshot_from_fixture(os.path.join(here, "fixtures", "hf", "v8-undeclared.json"),
                                 "demo/undeclared-pythia-clone")
    v8 = [f for f in verify(snap)["findings"] if f["check"] == "V8"]
    assert len(v8) == 1 and v8[0]["heuristic"] is True
    assert gate_counted(v8) == []  # never gate-counted


def test_known_bases_nonempty():
    from releaseseal.rules import load_pack
    assert load_pack("fingerprints-v1")["known_bases"], "V8 known_bases must be seeded"


def test_as_of_is_deterministic_not_wallclock(manifest):
    """V5 staleness uses the supplied/captured date, never now()."""
    stale = [c for c in manifest["cases"] if c["kind"] == "V5"]
    snap = stale[0]["snapshot"]
    a = verify(snap)["findings"]
    b = verify(snap, as_of_now=snap["captured_at"])["findings"]
    assert a == b
