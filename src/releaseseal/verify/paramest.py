"""Decoder-only transformer parameter estimate (DECISIONS.md D-02).

Coarse analytic estimate from config.json, used by V2 as a cross-check only.
"""
from __future__ import annotations

from typing import Optional

# FFN structure is chosen deterministically from config.model_type (D-21). Gated
# families use a 3-matrix (gate/up/down, SwiGLU-style) MLP; every other model_type
# is treated as a plain 2-matrix (up/down) MLP. The list must match the REAL
# architecture, not any test author's counting convention (D-23): GPT-NeoX
# (Pythia, GPT-NeoX-20B) uses a plain dense_h_to_4h / dense_4h_to_h GELU MLP, so
# gpt_neox is NOT gated — classifying it gated over-counts real NeoX models by
# ~hidden*inter (~24% on typical dims, beyond the ±20% tolerance).
_GATED_FAMILIES = {
    "llama", "mistral", "mixtral", "qwen2", "qwen2_moe", "qwen3", "gemma",
    "gemma2", "phi3", "stablelm", "starcoder2",
}


def _get_int(config: dict, *keys) -> Optional[int]:
    for k in keys:
        v = config.get(k)
        if isinstance(v, bool):
            continue
        if isinstance(v, int):
            return v
    return None


def estimate_params(config: Optional[dict]) -> Optional[int]:
    if not isinstance(config, dict):
        return None
    hidden = _get_int(config, "hidden_size", "n_embd", "d_model")
    layers = _get_int(config, "num_hidden_layers", "n_layer", "num_layers")
    heads = _get_int(config, "num_attention_heads", "n_head", "num_heads")
    vocab = _get_int(config, "vocab_size")
    inter = _get_int(config, "intermediate_size", "ffn_dim", "n_inner")
    if None in (hidden, layers, heads, vocab) or hidden <= 0 or heads <= 0:
        return None
    kv_heads = _get_int(config, "num_key_value_heads", "num_kv_heads") or heads
    if inter is None:
        inter = 4 * hidden  # conventional fallback

    gqa = kv_heads / heads
    attn = 2 * hidden * hidden * (1.0 + gqa)
    model_type = str(config.get("model_type", "")).lower()
    gated = model_type in _GATED_FAMILIES or bool(config.get("mlp_gated"))
    mlp = (3 if gated else 2) * hidden * inter
    per_layer = attn + mlp

    embeddings = vocab * hidden
    tie = config.get("tie_word_embeddings")
    lm_head = 0 if tie else vocab * hidden

    total = embeddings + layers * per_layer + lm_head
    return int(round(total))


def plausible_params(config) -> list:
    """Candidate parameter estimates (DECISIONS.md D-17 #1).

    When ``tie_word_embeddings`` is not stated in the config, the release may or
    may not tie the input/output embeddings, which shifts the count by one
    ``vocab*hidden`` matrix. Return both the tied and untied estimates so V2
    flags a claim only when it is outside tolerance of *every* plausible value —
    removing false positives on tied-embedding models whose config omits the flag.
    """
    base = estimate_params(config)
    if base is None:
        return []
    if not isinstance(config, dict):
        return [base]
    if config.get("tie_word_embeddings") is not None:
        return [base]  # tying is explicit; single estimate
    hidden = _get_int(config, "hidden_size", "n_embd", "d_model")
    vocab = _get_int(config, "vocab_size")
    if not hidden or not vocab:
        return [base]
    other = base - vocab * hidden if base > vocab * hidden else base + vocab * hidden
    return sorted({base, other})
