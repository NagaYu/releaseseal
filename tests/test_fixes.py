"""Regression tests for the D-17 / D-18 fixes — natural phrasing and real-card
patterns that previously produced false positives/negatives.
"""
from releaseseal.rules import load_packs
from releaseseal.snapshot.cardparse import extract_param_count
from releaseseal.snapshot.schema import empty_claims, finalize, make_card, make_file, make_snapshot, make_source
from releaseseal.verify.checks import (
    Context, v2_arch_scale, v4_doc_gaps, v5_staleness, v6_eval_consistency, v7_completeness,
)
from releaseseal.verify.paramest import estimate_params, plausible_params

CTX = Context(packs=load_packs())


def _snap(**over):
    claims = empty_claims(); claims.update(over.pop("claims", {}))
    card = make_card(yaml=over.pop("yaml", {}), prose=over.pop("prose", ""), claims=claims)
    base = dict(captured_at="2026-11-08", source=make_source("local", path="/x", revision="rev1"),
                config=over.pop("config", None), card=card)
    base.update(over)
    return finalize(make_snapshot(**base))


# --- D-17 #1: tied-embedding param estimate ---
def test_v2_tied_embedding_no_false_positive():
    # gpt2-like config with tie flag OMITTED; claim is the TIED count
    cfg = {"model_type": "gpt2", "hidden_size": 768, "num_hidden_layers": 12,
           "num_attention_heads": 12, "vocab_size": 50257, "intermediate_size": 3072,
           "max_position_embeddings": 1024}
    tied = cfg["vocab_size"] * cfg["hidden_size"]
    untied_est = estimate_params(cfg)
    claim = untied_est - tied  # the tied count
    assert len(plausible_params(cfg)) == 2
    snap = _snap(config=cfg, claims={"param_count": claim})
    assert [f for f in v2_arch_scale(snap, CTX) if f["code"] == "param_mismatch"] == []
    # a genuinely wrong claim (4x) still fires
    snap2 = _snap(config=cfg, claims={"param_count": untied_est * 4})
    assert any(f["code"] == "param_mismatch" for f in v2_arch_scale(snap2, CTX))


# --- D-21/D-23: FFN structure matches the REAL architecture ---
def test_v2_gated_family_true_count_clean():
    # a gated family (llama) stating its true 3-matrix (SwiGLU) count is clean
    cfg = {"model_type": "llama", "hidden_size": 2048, "num_hidden_layers": 22,
           "num_attention_heads": 16, "num_key_value_heads": 4, "vocab_size": 32000,
           "intermediate_size": 5632, "max_position_embeddings": 8192, "tie_word_embeddings": False}
    est = estimate_params(cfg)
    assert [f for f in v2_arch_scale(_snap(config=cfg, claims={"param_count": est}), CTX)
            if f["code"] == "param_mismatch"] == []


def test_v2_gpt_neox_is_plain_not_gated():
    # D-23: GPT-NeoX uses a plain 2-matrix MLP; it must NOT be in the gated set
    from releaseseal.verify.paramest import _GATED_FAMILIES
    assert "gpt_neox" not in _GATED_FAMILIES and "gptneox" not in _GATED_FAMILIES
    cfg = {"model_type": "gpt_neox", "hidden_size": 2048, "num_hidden_layers": 24,
           "num_attention_heads": 16, "num_key_value_heads": 16, "vocab_size": 50304,
           "intermediate_size": 8192, "max_position_embeddings": 2048,
           "tie_word_embeddings": False}
    plain = estimate_params(cfg)  # now the plain (2-matrix) count
    # the true plain count is clean
    assert [f for f in v2_arch_scale(_snap(config=cfg, claims={"param_count": plain}), CTX)
            if f["code"] == "param_mismatch"] == []
    # a gated-inflated claim (+ hidden*intermediate, ~24%) is correctly flagged
    gated_inflated = plain + cfg["hidden_size"] * cfg["intermediate_size"] * cfg["num_hidden_layers"]
    assert any(f["code"] == "param_mismatch"
               for f in v2_arch_scale(_snap(config=cfg, claims={"param_count": gated_inflated}), CTX))


# --- D-17 #3: rope_theta context extension ---
def test_v2_rope_theta_exempts_context():
    cfg = {"model_type": "llama", "hidden_size": 1024, "num_hidden_layers": 8,
           "num_attention_heads": 16, "vocab_size": 32000, "intermediate_size": 2816,
           "max_position_embeddings": 4096, "rope_theta": 5_000_000.0}
    snap = _snap(config=cfg, claims={"context_length": 200000})
    assert [f for f in v2_arch_scale(snap, CTX) if f["code"] == "context_mismatch"] == []


# --- D-17 #2: claim extractor ignores tokens / sibling names ---
def test_param_extractor_context_required():
    assert extract_param_count({}, "Trained on 623 billion tokens.")[0] is None
    assert extract_param_count({}, "A sibling of Yi-34B.")[0] is None
    assert extract_param_count({}, "This 7B model is great.")[0] == 7_000_000_000
    assert extract_param_count({}, "It has 1.3B parameters.")[0] == 1_300_000_000


# --- D-18 #6: V4 robust to natural phrasing ---
def test_v4_natural_phrasing_no_false_gaps():
    cfg = {"model_type": "llama", "hidden_size": 1024, "num_hidden_layers": 8,
           "num_attention_heads": 16, "vocab_size": 32000, "intermediate_size": 2816,
           "max_position_embeddings": 4096}
    prose = (
        "# Natural Card\n"
        "The model was pretrained and then fine-tuned.\n"
        "We evaluated on standard benchmarks.\n"
        "Training used 1024 GPU-hours.\n"
        "We tracked carbon emissions.\n"
        "The training data is a public corpus.\n"
        "Intended for text generation.\n"
        "To integrate the model, load it with transformers.\n"
        "Out of scope: medical advice.\n"
        "It accepts text and generates text.\n"
        "Available on the model hub.\n"
        "Our copyright policy covers data rights.\n"
        "A public summary of training content is provided.\n"
    )
    snap = _snap(config=cfg, prose=prose,
                 claims={"license": "apache-2.0", "param_count": 1},
                 yaml={"license": "apache-2.0"},
                 model_index=[{"results": [{"dataset": {"name": "mmlu"},
                                            "metrics": [{"name": "accuracy", "value": 0.6}]}]}])
    gaps = v4_doc_gaps(snap, CTX)
    assert gaps == [], [f["evidence"]["field"] for f in gaps]


# --- D-22: provider-doc items need a substantive phrase OR a reference field,
# not a bare word ---
_NEAR_COMPLETE = (
    "# Card\nThe model was pretrained and fine-tuned.\nWe evaluated on benchmarks.\n"
    "Training used 1024 GPU-hours.\nWe tracked carbon emissions.\n"
    "The training data is a public corpus.\nIntended for text generation.\n"
    "To integrate the model, load it with transformers.\nOut of scope: medical advice.\n"
    "It accepts text and generates text.\nAvailable on the model hub.\n"
    "A public summary of training content is provided.\n"
)


def _card(prose, yaml=None):
    cfg = {"model_type": "llama", "hidden_size": 1024, "num_hidden_layers": 8,
           "num_attention_heads": 16, "vocab_size": 32000, "intermediate_size": 2816,
           "max_position_embeddings": 4096}
    return _snap(config=cfg, prose=prose, claims={"license": "apache-2.0", "param_count": 1},
                 yaml=dict({"license": "apache-2.0"}, **(yaml or {})),
                 model_index=[{"results": [{"dataset": {"name": "mmlu"},
                                            "metrics": [{"name": "accuracy", "value": 0.6}]}]}])


def test_v4_copyright_bare_word_not_satisfied():
    # mentions the word "copyright" but states no policy / reference -> flagged
    snap = _card(_NEAR_COMPLETE + "Copyright 2024 Holdout Lab.\n")
    assert any(f["evidence"]["field"] == "cop.copyright_policy" for f in v4_doc_gaps(snap, CTX))


def test_v4_copyright_phrase_satisfies():
    snap = _card(_NEAR_COMPLETE + "Our copyright policy covers data rights.\n")
    assert not any(f["evidence"]["field"] == "cop.copyright_policy" for f in v4_doc_gaps(snap, CTX))


def test_v4_copyright_reference_field_satisfies():
    snap = _card(_NEAR_COMPLETE + "Copyright 2024.\n",
                 yaml={"copyright_policy_url": "https://example.test/policy"})
    assert not any(f["evidence"]["field"] == "cop.copyright_policy" for f in v4_doc_gaps(snap, CTX))


# --- D-18 #7 / D-17 #4: V6 natural claims + hyperparameter exclusion ---
def test_v6_natural_unsourced_claim_detected():
    snap = _snap(prose="# M\nThe model achieves 88.0 on GSM8K.\n", model_index=None)
    assert any(f["code"] == "unsourced_claim" for f in v6_eval_consistency(snap, CTX))


def test_v6_hyperparameters_not_flagged():
    prose = "# M\nnum_gpus: 8\nbatch_size: 8\nTraining Loss: 2.0\nlearning_rate: 3\n"
    snap = _snap(prose=prose, model_index=None)
    assert [f for f in v6_eval_consistency(snap, CTX) if f["code"] == "unsourced_claim"] == []


# --- D-18 #8: V5 result-file source drift ---
def test_v5_result_file_source_drift():
    snap = _snap(result_files={"eval/r.json": {"source_checkpoint": "othersha",
                                               "results": {"mmlu": {"accuracy": 0.6}}}})
    assert any(f["code"] == "revision_drift" for f in v5_staleness(snap, CTX))


# --- D-18 #9 / D-17 #5: V7 spm.model + chat-template-file ---
def test_v7_spm_model_recognized():
    snap = _snap(tokenizer_config={"tokenizer_class": "DebertaV2"},
                 files=[make_file("spm.model", 10, "a" * 64, "streamed")])
    assert [f for f in v7_completeness(snap, CTX) if f["code"] == "tokenizer_missing"] == []


def test_v7_chat_template_file_missing():
    snap = _snap(tokenizer_config={"tokenizer_class": "X", "chat_template_file": "chat_template.jinja"},
                 chat_template=None,
                 files=[make_file("tokenizer.json", 10, "b" * 64, "streamed")])
    assert any(f["code"] == "chat_template_file_missing" for f in v7_completeness(snap, CTX))


# --- D-26: V6 scale-aware prose-vs-structured value comparison ---
def test_v6_prose_contradicts_structured_fires():
    mi = [{"results": [{"dataset": {"name": "mmlu"},
                        "metrics": [{"name": "accuracy", "value": 0.60}]}]}]
    snap = _snap(model_index=mi, prose="# M\nThe model scores 74.0 on MMLU.\n")
    assert any(f["code"] == "eval_value_mismatch" for f in v6_eval_consistency(snap, CTX))


def test_v6_prose_scale_match_silent():
    # prose 60.0 (0-100) vs structured 0.60 (fraction) agree -> no V6
    mi = [{"results": [{"dataset": {"name": "mmlu"},
                        "metrics": [{"name": "accuracy", "value": 0.60}]}]}]
    snap = _snap(model_index=mi, prose="# M\nThe model achieves 60.0 on MMLU.\n")
    assert v6_eval_consistency(snap, CTX) == []


# --- D-24: content-word V4 matching (stem + windowed co-occurrence) ---
def test_v4_content_word_handles_inflection_and_order():
    from releaseseal.verify import checks as _c
    cfg = {"model_type": "llama", "hidden_size": 1024, "num_hidden_layers": 8,
           "num_attention_heads": 16, "vocab_size": 32000, "intermediate_size": 2816,
           "max_position_embeddings": 4096}
    # every item documented in varied, inflected, reordered natural wording
    prose = (
        "# Card\n"
        "Built and released by Acme, the responsible provider.\n"
        "A decoder-only transformer architecture.\n"
        "Intended for general text generation and research use cases.\n"
        "Inputs and outputs are text; no other modalities.\n"
        "The training corpus is a curated mixture of public web text.\n"
        "Pretrained with AdamW, then supervised fine-tuning.\n"
        "Validated by running the model over an untouched held-out test set.\n"
        "Training compute was about 1024 GPU-hours.\n"
        "Energy consumption and carbon emissions were tracked.\n"
        "Out-of-scope and prohibited uses are described.\n"
        "Technical means for integration into downstream systems are given.\n"
        "Our copyright policy covers the rights in the training data.\n"
        "A public summary of the training content is provided.\n"
        "Distributed for download on the model hub.\n"
    )
    snap = _snap(config=cfg, prose=prose, claims={"license": "apache-2.0", "param_count": 1},
                 yaml={"license": "apache-2.0"},
                 model_index=[{"results": [{"dataset": {"name": "mmlu"},
                                            "metrics": [{"name": "accuracy", "value": 0.6}]}]}])
    gaps = _c.v4_doc_gaps(snap, CTX)
    assert gaps == [], [f["evidence"]["field"] for f in gaps]
