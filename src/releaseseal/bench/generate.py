"""Bench Part A — synthetic release generator (SPEC.md §6, design §5).

Small synthetic releases (metadata + tiny stand-in artifacts; NO real weights)
with planted V1–V7 discrepancies and clean releases (incl. near-miss cleans).
Fully seeded: same seed -> identical bytes (tested).
"""
from __future__ import annotations

import copy
import hashlib
import random
from typing import Optional

from .. import BENCH_MANIFEST_SCHEMA
from ..canonical import canonical_sha256
from ..snapshot.schema import empty_claims, finalize, make_card, make_file, make_snapshot, make_source

CLASSES = ("V1", "V2", "V3", "V4", "V5", "V6", "V7")

# One sentence per keyword-only Annex/CoP item (SPEC.md §6; dropped to plant V4).
_DOC_SENTENCES = {
    "xi.training_process": "The training process followed a standard pretraining and fine-tuning recipe.",
    "xi.testing_process": "A testing process with a documented evaluation procedure was applied.",
    "xi.compute": "Training compute was approximately 2048 accelerator-days.",
    "xi.energy": "Energy consumption and estimated carbon emissions were recorded during training.",
    "xi.data_summary": "Training data consisted of a documented mixture of public text corpora.",
    "xi.intended_use": "Intended use is general-purpose English text generation.",
    "xii.downstream_integration": "Technical means for integration into AI systems are provided to downstream providers.",
    "xii.acceptable_use": "Acceptable use and out-of-scope uses are described for operators.",
    "xii.io_modality": "Input and output modality is text, encoded as UTF-8.",
    "cop.distribution": "The distribution channel is the public model hub.",
    "cop.copyright_policy": "A copyright policy consistent with the provider duty is published.",
    "cop.training_content_summary": "A public training content summary accompanies this release.",
}
_DOC_ORDER = list(_DOC_SENTENCES.keys())


def _hex(rng: random.Random, n: int = 64) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(n))


def _prose(name: str, items: list[str]) -> str:
    lines = [f"# {name}", "", "A compact decoder-only language model."]
    for item in items:
        lines.append(_DOC_SENTENCES[item])
    return "\n".join(lines) + "\n"


def _base_config(rng: random.Random) -> dict:
    hidden = rng.choice([512, 768, 1024, 2048])
    layers = rng.choice([8, 12, 16, 24])
    heads = rng.choice([8, 16])
    kv = rng.choice([heads, heads // 2]) or heads
    vocab = rng.choice([32000, 32768, 50257, 128256])
    inter = hidden * rng.choice([3, 4])
    ctx = rng.choice([2048, 4096, 8192])
    return {
        "model_type": "llama",
        "hidden_size": hidden,
        "num_hidden_layers": layers,
        "num_attention_heads": heads,
        "num_key_value_heads": kv,
        "vocab_size": vocab,
        "intermediate_size": inter,
        "max_position_embeddings": ctx,
        "tie_word_embeddings": False,
        "torch_dtype": "bfloat16",
    }


def _model_index(value: float = 0.72) -> list:
    return [{
        "name": "bench-model",
        "results": [{
            "task": {"type": "text-generation", "name": "Text Generation"},
            "dataset": {"name": "mmlu", "type": "mmlu"},
            "metrics": [{"type": "accuracy", "name": "accuracy", "value": value}],
        }],
    }]


def _standard_files(rng: random.Random, weight_size: int, *, extra=None, drop=None) -> list:
    names = [
        ("config.json", 1024),
        ("generation_config.json", 256),
        ("tokenizer_config.json", 2048),
        ("tokenizer.json", 400000),
        ("README.md", 4096),
        ("model.safetensors", weight_size),
        ("model.safetensors.index.json", 1200),
    ]
    drop = set(drop or ())
    files = []
    for path, size in names:
        if path in drop:
            continue
        files.append(make_file(path, size=size, sha256=_hex(rng), hash_source="streamed"))
    for e in (extra or []):
        files.append(make_file(e[0], size=e[1], sha256=_hex(rng), hash_source="streamed"))
    files.sort(key=lambda f: f["path"])
    return files


def _build_clean(rng: random.Random, name: str, *, profile: str = "root") -> dict:
    from ..verify.paramest import estimate_params as estimate

    config = _base_config(rng)
    weight_size = config["hidden_size"] * config["num_hidden_layers"] * 100000
    est = estimate(config)

    claims = empty_claims()
    claims["param_count"] = est
    claims["param_count_text"] = f"~{est}"
    claims["context_length"] = config["max_position_embeddings"]
    claims["architecture"] = None
    claims["license"] = "apache-2.0"

    yaml = {
        "license": "apache-2.0",
        "pipeline_tag": "text-generation",
        "library_name": "transformers",
        "tags": ["text-generation"],
    }
    lineage = {}
    files_extra = []

    if profile == "merge":
        bases = ["bench/parent-a", "bench/parent-b"]
        claims["base_model"] = bases
        claims["base_model_relation"] = "merge"
        yaml["base_model"] = bases
        yaml["base_model_relation"] = "merge"
        lineage = {b: {"license": "apache-2.0", "notice_present_in_ancestor": False} for b in bases}
    elif profile == "gemma":
        base = "google/gemma-2-2b"
        claims["license"] = "gemma"
        yaml["license"] = "gemma"
        claims["base_model"] = [base]
        claims["base_model_relation"] = "finetune"
        yaml["base_model"] = [base]
        lineage = {base: {"license": "gemma", "notice_present_in_ancestor": True}}
        files_extra = [("NOTICE", 512)]
    elif profile == "openrail":
        base = "bigscience/bloom-560m"
        claims["license"] = "bigscience-openrail-m"
        yaml["license"] = "bigscience-openrail-m"
        claims["base_model"] = [base]
        claims["base_model_relation"] = "finetune"
        yaml["base_model"] = [base]
        lineage = {base: {"license": "bigscience-openrail-m", "notice_present_in_ancestor": True}}
        files_extra = [("NOTICE", 512)]
    elif profile == "noncommercial":
        claims["license"] = "cc-by-nc-4.0"
        yaml["license"] = "cc-by-nc-4.0"

    yaml["model-index"] = _model_index()
    if claims.get("base_model"):
        yaml["base_model_relation"] = claims["base_model_relation"]

    prose = _prose(name, _DOC_ORDER)
    card = make_card(yaml=yaml, prose=prose, claims=claims)

    weight_map = {
        "model.embed_tokens.weight": "model.safetensors",
        "lm_head.weight": "model.safetensors",
    }
    sti = {"metadata": {"total_size": weight_size}, "weight_map": weight_map}

    gen_cfg = {"eos_token_id": 2, "bos_token_id": 1, "pad_token_id": 0, "max_new_tokens": 256}
    tok_cfg = {"model_max_length": config["max_position_embeddings"], "tokenizer_class": "LlamaTokenizer"}

    files = _standard_files(rng, weight_size, extra=files_extra)

    snap = make_snapshot(
        captured_at="2026-11-08",
        source=make_source("local", repo_id=f"bench/{name}", revision="rev-" + _hex(rng, 8), path=f"/bench/{name}"),
        files=files,
        card=card,
        config=config,
        generation_config=gen_cfg,
        tokenizer_config=tok_cfg,
        chat_template="{{ messages }}",
        safetensors_index=sti,
        model_index=yaml["model-index"],
        result_files={},
        lineage=lineage,
    )
    return snap


# --- mutators: each breaks exactly its class, leaving others clean ----------

def _mutate_v1(snap, variant, rng):
    files = snap["files"]
    paths = {f["path"] for f in files}
    sti = snap["safetensors_index"]
    if variant == 0:  # missing_file
        sti["weight_map"] = {"model.embed_tokens.weight": "model-weights.safetensors"}
        snap["files"] = [f for f in files if f["path"] != "model.safetensors"]
        sti["metadata"].pop("total_size", None)
    elif variant == 1:  # undocumented_weight
        snap["files"].append(make_file("extra.safetensors", size=123456, sha256=_hex(rng), hash_source="streamed"))
        snap["files"].sort(key=lambda f: f["path"])
    elif variant == 2:  # size_mismatch
        size = next(f["size"] for f in files if f["path"] == "model.safetensors")
        sti["metadata"]["total_size"] = size * 2
    else:  # hash_mismatch
        sha = next(f["sha256"] for f in files if f["path"] == "model.safetensors")
        snap["card"]["yaml"]["file_checksums"] = {"model.safetensors": "f" * 64 if sha != "f" * 64 else "e" * 64}


def _mutate_v2(snap, variant, rng):
    claims = snap["card"]["claims"]
    config = snap["config"]
    if variant == 0:  # param_mismatch
        claims["param_count"] = claims["param_count"] * 3
        claims["param_count_text"] = f"~{claims['param_count']}"
    elif variant == 1:  # context_mismatch
        claims["context_length"] = config["max_position_embeddings"] * 8
    elif variant == 2:  # architecture_mismatch
        claims["architecture"] = "mistral"
    else:  # relation_mismatch
        base = "bench/parent-x"
        claims["base_model"] = [base]
        snap["card"]["yaml"]["base_model"] = [base]
        snap["lineage"] = {base: {"license": "apache-2.0", "notice_present_in_ancestor": False}}
        rel = ("merge", "adapter", "quantized")[rng.randrange(3)]
        claims["base_model_relation"] = rel
        snap["card"]["yaml"]["base_model_relation"] = rel
        # merge needs >=2 bases (we gave 1); adapter/quantized need adapter/quant artifacts (absent) -> fires


def _mutate_v3(snap, variant, rng):
    claims = snap["card"]["claims"]
    yaml = snap["card"]["yaml"]
    if variant % 2 == 0:  # license_incompatible
        base = "meta-llama/Meta-Llama-3-8B"
        claims["base_model"] = [base]
        yaml["base_model"] = [base]
        claims["base_model_relation"] = "finetune"
        yaml["base_model_relation"] = "finetune"
        claims["license"] = "apache-2.0"
        yaml["license"] = "apache-2.0"
        snap["lineage"] = {base: {"license": "llama-3-community", "notice_present_in_ancestor": True}}
        snap["files"].append(make_file("NOTICE", size=256, sha256=_hex(rng), hash_source="streamed"))
        snap["files"].sort(key=lambda f: f["path"])
    else:  # attribution_missing
        base = "google/gemma-2-9b"
        claims["base_model"] = [base]
        yaml["base_model"] = [base]
        claims["base_model_relation"] = "finetune"
        yaml["base_model_relation"] = "finetune"
        claims["license"] = "gemma"
        yaml["license"] = "gemma"
        snap["lineage"] = {base: {"license": "gemma", "notice_present_in_ancestor": True}}
        # no NOTICE file -> attribution_missing


def _mutate_v4(snap, variant, rng):
    item = _DOC_ORDER[variant % len(_DOC_ORDER)]
    kept = [i for i in _DOC_ORDER if i != item]
    name = snap["card"]["prose"].splitlines()[0].lstrip("# ").strip() or "bench-model"
    snap["card"]["prose"] = _prose(name, kept)


def _mutate_v5(snap, variant, rng):
    yaml = snap["card"]["yaml"]
    if variant % 2 == 0:  # revision_drift
        yaml["revision"] = "rev-deadbeef"
    else:  # stale_as_of
        yaml["as_of"] = "2023-01-01"


def _mutate_v6(snap, variant, rng):
    v = variant % 3
    if v == 0:  # internal conflict
        mi = copy.deepcopy(snap["model_index"])
        mi.append({
            "name": "bench-model",
            "results": [{
                "task": {"type": "text-generation"},
                "dataset": {"name": "mmlu", "type": "mmlu"},
                "metrics": [{"type": "accuracy", "name": "accuracy", "value": 0.88}],
            }],
        })
        snap["model_index"] = mi
        snap["card"]["yaml"]["model-index"] = mi
    elif v == 1:  # value mismatch vs result file
        snap["result_files"] = {"results/eval_results.json": {"results": {"mmlu": {"accuracy": 0.95}}}}
        snap["files"].append(make_file("results/eval_results.json", size=512, sha256=_hex(rng), hash_source="streamed"))
        snap["files"].sort(key=lambda f: f["path"])
    else:  # unsourced prose claim
        snap["card"]["prose"] += "\nARC: 55.5\n"


def _mutate_v7(snap, variant, rng):
    v = variant % 4
    if v == 0:  # tokenizer_missing
        snap["files"] = [f for f in snap["files"] if f["path"] != "tokenizer.json"]
    elif v == 1:  # chat_template_missing
        snap["card"]["yaml"]["tags"] = ["text-generation", "conversational"]
        snap["chat_template"] = None
    elif v == 2:  # genconfig_inconsistent
        snap["generation_config"]["eos_token_id"] = snap["config"]["vocab_size"] + 5
    else:  # index_incomplete
        shard = "model-00001-of-00002.safetensors"
        snap["safetensors_index"]["weight_map"] = {"model.embed_tokens.weight": shard}
        snap["safetensors_index"]["metadata"].pop("total_size", None)
        snap["files"] = [f for f in snap["files"] if f["path"] != "model.safetensors"]
        snap["files"].append(make_file(shard, size=500000, sha256=_hex(rng), hash_source="streamed"))
        snap["files"].sort(key=lambda f: f["path"])


_MUTATORS = {
    "V1": _mutate_v1, "V2": _mutate_v2, "V3": _mutate_v3, "V4": _mutate_v4,
    "V5": _mutate_v5, "V6": _mutate_v6, "V7": _mutate_v7,
}

_CLEAN_PROFILES = ["root", "root", "root", "root", "merge", "gemma", "openrail", "noncommercial"]


def generate(seed: int = 0, per_class: int = 12, n_clean: int = 36) -> dict:
    rng = random.Random(seed)
    cases = []
    idx = 0
    for cls in CLASSES:
        for i in range(per_class):
            idx += 1
            snap = _build_clean(rng, f"case-{idx:04d}", profile="root")
            _MUTATORS[cls](snap, i, rng)
            cases.append({
                "id": f"case-{idx:04d}",
                "kind": cls,
                "expected": [cls],
                "snapshot": finalize(snap),
            })
    for i in range(n_clean):
        idx += 1
        profile = _CLEAN_PROFILES[i % len(_CLEAN_PROFILES)]
        snap = _build_clean(rng, f"case-{idx:04d}", profile=profile)
        cases.append({
            "id": f"case-{idx:04d}",
            "kind": "clean",
            "expected": [],
            "snapshot": finalize(snap),
        })

    composition = {cls: per_class for cls in CLASSES}
    composition["clean"] = n_clean
    cases_sha = canonical_sha256(cases)
    return {
        "schema_version": BENCH_MANIFEST_SCHEMA,
        "seed": seed,
        "cases_sha256": cases_sha,
        "composition": composition,
        "cases": cases,
    }
