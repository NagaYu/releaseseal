"""Class-specific targeted negatives (audit note 3): for each check, a case
crafted to sit near that check's boundary but which must NOT fire it.
"""
from releaseseal.rules import load_packs
from releaseseal.snapshot.schema import empty_claims, finalize, make_card, make_file, make_snapshot, make_source
from releaseseal.verify.checks import (
    Context, v1_artifact_record, v2_arch_scale, v3_license_lineage, v4_doc_gaps,
    v5_staleness, v6_eval_consistency, v7_completeness, v8_undeclared_derivation,
)
from releaseseal.verify.paramest import estimate_params

CTX = Context(packs=load_packs())
CONFIG = {"model_type": "llama", "hidden_size": 1024, "num_hidden_layers": 12,
          "num_attention_heads": 16, "num_key_value_heads": 16, "vocab_size": 32000,
          "intermediate_size": 3072, "max_position_embeddings": 4096, "tie_word_embeddings": False}


def _snap(**over):
    claims = empty_claims()
    claims.update(over.pop("claims", {}))
    card = make_card(yaml=over.pop("yaml", {}), prose=over.pop("prose", ""), claims=claims)
    base = dict(captured_at="2026-11-08", source=make_source("local", path="/x", revision="rev1"),
                config=CONFIG, card=card)
    base.update(over)
    return finalize(make_snapshot(**base))


def test_v1_negative_consistent_index():
    snap = _snap(
        files=[make_file("model.safetensors", size=1000, sha256="a" * 64, hash_source="streamed")],
        safetensors_index={"metadata": {"total_size": 1000},
                           "weight_map": {"w": "model.safetensors"}},
    )
    assert v1_artifact_record(snap, CTX) == []


def test_v2_negative_claims_match_config():
    est = estimate_params(CONFIG)
    snap = _snap(claims={"param_count": est, "context_length": 4096,
                         "architecture": "llama", "base_model_relation": None})
    assert v2_arch_scale(snap, CTX) == []


def test_v3_negative_compatible_license_with_notice():
    snap = _snap(
        claims={"license": "gemma", "base_model": ["g/base"]},
        files=[make_file("NOTICE", size=10, sha256="b" * 64, hash_source="streamed")],
        lineage={"g/base": {"license": "gemma", "notice_present_in_ancestor": True, "depth": 1}},
    )
    assert v3_license_lineage(snap, CTX) == []


def test_v4_negative_all_docs_present():
    from releaseseal.bench.generate import _DOC_SENTENCES
    prose = "# m\n" + "\n".join(_DOC_SENTENCES.values())
    snap = _snap(claims={"license": "apache-2.0", "param_count": 1}, prose=prose,
                 yaml={"license": "apache-2.0"}, model_index=[{"results": []}])
    assert v4_doc_gaps(snap, CTX) == []


def test_v5_negative_no_drift_current_as_of():
    snap = _snap(yaml={"revision": "rev1", "as_of": "2026-11-08"})
    assert v5_staleness(snap, CTX) == []


def test_v6_negative_sourced_consistent():
    mi = [{"results": [{"dataset": {"name": "mmlu"},
                        "metrics": [{"name": "accuracy", "value": 0.7}]}]}]
    snap = _snap(model_index=mi, prose="Scores are reported in the model-index.")
    assert v6_eval_consistency(snap, CTX) == []


def test_v7_negative_complete_nonchat():
    snap = _snap(
        files=[make_file("tokenizer.json", size=10, sha256="c" * 64, hash_source="streamed")],
        tokenizer_config={"tokenizer_class": "X"},
        generation_config={"eos_token_id": 2},
        yaml={"tags": ["text-generation"]},
    )
    assert v7_completeness(snap, CTX) == []


def test_v8_negative_base_declared():
    snap = _snap(claims={"base_model": ["some/base"]})
    assert v8_undeclared_derivation(snap, CTX) == []
