"""Verification checks V1–V8 (SPEC.md §3, design §4.2).

Each check is ``(snapshot, ctx) -> list[finding]``. Pure and deterministic. V1–V7
are gate-counted; V8 is heuristic/signal-only and never gate-counted.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from ..rules import load_packs, pack_versions
from . import textmatch as _tm
from .fingerprint import DEFAULT_FIELDS, fingerprint
from .findings import finding, make_evidence
from .paramest import estimate_params, plausible_params

V2_PARAM_TOLERANCE = 0.20  # D-02
_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_PROSE_CLAIM_RE = re.compile(
    r"(?im)^\s*[-*]?\s*(?P<bench>[A-Za-z][A-Za-z0-9 _\-]{1,24}?)\s*[:=]\s*(?P<val>\d{1,3}(?:\.\d+)?)\s*%?\s*$"
)


@dataclass
class Context:
    packs: dict
    as_of_now: Optional[str] = None  # ISO date; default -> snapshot.captured_at (D-10)

    @classmethod
    def default(cls, pack_ids=None) -> "Context":
        return cls(packs=load_packs(pack_ids))

    def versions(self) -> dict:
        return pack_versions(self.packs)


# --- small helpers ---------------------------------------------------------

def _files(snap) -> list:
    return snap.get("files") or []


def _file_paths(snap) -> set:
    return {f.get("path") for f in _files(snap) if f.get("path")}


def _basenames(snap) -> set:
    return {p.rsplit("/", 1)[-1] for p in _file_paths(snap)}


def _has_notice(snap) -> bool:
    for p in _file_paths(snap):
        base = p.rsplit("/", 1)[-1].upper()
        if base.startswith("NOTICE") or base.startswith("ATTRIBUTION") or "NOTICE" in base:
            return True
    yaml = (snap.get("card") or {}).get("yaml") or {}
    return bool(yaml.get("attribution"))


def _claims(snap) -> dict:
    return (snap.get("card") or {}).get("claims") or {}


# ===========================================================================
# V1 — Artifact–record mismatch
# ===========================================================================

def v1_artifact_record(snap, ctx) -> list:
    out = []
    paths = _file_paths(snap)
    sti = snap.get("safetensors_index")
    if isinstance(sti, dict):
        wm = sti.get("weight_map") or {}
        referenced = sorted(set(wm.values()))
        for shard in referenced:
            if shard not in paths:
                out.append(finding(
                    "V1", "missing_file", "high",
                    f"safetensors index references weight shard '{shard}' not present in the release.",
                    evidence=make_evidence(file="model.safetensors.index.json",
                                           field="weight_map", expected=shard, actual="absent"),
                ))
        # undocumented weight files
        if referenced:
            for p in sorted(paths):
                base = p.rsplit("/", 1)[-1]
                if base.endswith(".safetensors") and p not in referenced:
                    out.append(finding(
                        "V1", "undocumented_weight", "medium",
                        f"Weight file '{p}' is present but not referenced by the safetensors index.",
                        evidence=make_evidence(file=p, field="weight_map",
                                               expected="referenced in index", actual="not referenced"),
                    ))
        # total_size consistency
        meta = sti.get("metadata") or {}
        total = meta.get("total_size")
        if isinstance(total, int) and referenced:
            size_by_path = {f["path"]: f.get("size") for f in _files(snap)}
            summed = 0
            known = True
            for shard in referenced:
                s = size_by_path.get(shard)
                if not isinstance(s, int):
                    known = False
                    break
                summed += s
            if known and summed > 0 and abs(summed - total) / total > 0.01:
                out.append(finding(
                    "V1", "size_mismatch", "medium",
                    f"safetensors index total_size {total} disagrees with summed shard sizes {summed}.",
                    evidence=make_evidence(file="model.safetensors.index.json",
                                           field="metadata.total_size", expected=summed, actual=total),
                ))
    # declared per-file checksums vs recorded file sha256
    yaml = (snap.get("card") or {}).get("yaml") or {}
    checks = yaml.get("file_checksums")
    if isinstance(checks, dict):
        sha_by_path = {f["path"]: f.get("sha256") for f in _files(snap)}
        for path, declared in sorted(checks.items()):
            actual = sha_by_path.get(path)
            if actual is not None and declared is not None and actual != declared:
                out.append(finding(
                    "V1", "hash_mismatch", "high",
                    f"Declared checksum for '{path}' does not match the release artifact's hash.",
                    evidence=make_evidence(file=path, field="file_checksums",
                                           expected=declared, actual=actual),
                ))
    return out


# ===========================================================================
# V2 — Architecture & scale claims
# ===========================================================================

def v2_arch_scale(snap, ctx) -> list:
    out = []
    claims = _claims(snap)
    config = snap.get("config") or {}
    # param count — flag only if outside tolerance of EVERY plausible estimate
    # (tied/untied ambiguity when the config omits tie_word_embeddings; D-17 #1)
    claimed = claims.get("param_count")
    estimates = plausible_params(config)
    if isinstance(claimed, int) and estimates:
        def _ok(e):
            return e * (1 - V2_PARAM_TOLERANCE) <= claimed <= e * (1 + V2_PARAM_TOLERANCE)
        if not any(_ok(e) for e in estimates):
            nearest = min(estimates, key=lambda e: abs(e - claimed))
            out.append(finding(
                "V2", "param_mismatch", "high",
                f"Card claims ~{claimed:,} parameters but config implies ~{nearest:,} (outside ±{int(V2_PARAM_TOLERANCE*100)}%).",
                evidence=make_evidence(file="README.md", field="param_count",
                                       expected=f"~{nearest}", actual=claimed),
            ))
    # context length — exempt rope scaling expressed as rope_scaling OR a
    # non-default rope_theta (D-17 #3)
    claimed_ctx = claims.get("context_length")
    cfg_ctx = config.get("max_position_embeddings")
    rope_theta = config.get("rope_theta")
    rope_extended = bool(config.get("rope_scaling")) or (isinstance(rope_theta, (int, float)) and rope_theta > 10000)
    if isinstance(claimed_ctx, int) and isinstance(cfg_ctx, int) and cfg_ctx > 0:
        ratio = claimed_ctx / cfg_ctx
        if claimed_ctx != cfg_ctx and not rope_extended and (ratio < 0.5 or ratio > 2.0):
            out.append(finding(
                "V2", "context_mismatch", "medium",
                f"Card claims context length {claimed_ctx} but config max_position_embeddings is {cfg_ctx}.",
                evidence=make_evidence(file="config.json", field="max_position_embeddings",
                                       expected=claimed_ctx, actual=cfg_ctx),
            ))
    # architecture family
    arch = claims.get("architecture")
    mtype = config.get("model_type")
    if isinstance(arch, str) and isinstance(mtype, str):
        a = arch.strip().lower()
        if a and a not in mtype.lower() and mtype.lower() not in a:
            out.append(finding(
                "V2", "architecture_mismatch", "medium",
                f"Card claims architecture '{arch}' but config model_type is '{mtype}'.",
                evidence=make_evidence(file="config.json", field="model_type",
                                       expected=arch, actual=mtype),
            ))
    # relation vs artifacts
    rel = claims.get("base_model_relation")
    bases = claims.get("base_model") or []
    basenames = _basenames(snap)
    has_full_shards = any(b.endswith(".safetensors") and "adapter" not in b for b in basenames) or \
        isinstance(snap.get("safetensors_index"), dict)
    if rel == "adapter":
        has_adapter = "adapter_config.json" in basenames or any("adapter" in b for b in basenames)
        if has_full_shards and not has_adapter:
            out.append(finding(
                "V2", "relation_mismatch", "medium",
                "base_model_relation is 'adapter' but the release carries full weights and no adapter artifacts.",
                evidence=make_evidence(field="base_model_relation",
                                       expected="adapter artifacts", actual="full weights, no adapter"),
            ))
    elif rel == "quantized":
        quantized = bool(config.get("quantization_config")) or any("quant" in b.lower() for b in basenames)
        if not quantized:
            out.append(finding(
                "V2", "relation_mismatch", "medium",
                "base_model_relation is 'quantized' but no quantization config or quantized artifacts are present.",
                evidence=make_evidence(field="base_model_relation",
                                       expected="quantization_config", actual="absent"),
            ))
    elif rel == "merge":
        if len(bases) < 2:
            out.append(finding(
                "V2", "relation_mismatch", "medium",
                f"base_model_relation is 'merge' but only {len(bases)} base model(s) are declared.",
                evidence=make_evidence(field="base_model",
                                       expected=">=2 base models", actual=len(bases)),
            ))
    return out


# ===========================================================================
# V3 — License lineage
# ===========================================================================

def v3_license_lineage(snap, ctx) -> list:
    out = []
    claims = _claims(snap)
    ancestors = list(claims.get("base_model") or [])
    lineage = snap.get("lineage") or {}
    if not ancestors and not lineage:
        return out  # root release; nothing to walk
    licpack = ctx.packs.get("license-terms-v1", {})
    table = licpack.get("licenses", {})
    declared = claims.get("license")
    declared_known = isinstance(declared, str) and declared in table

    if ancestors and not declared_known:
        out.append(finding(
            "V3", "license_unknown", "low",
            f"Release declares license '{declared}' which is not in the license-terms table; "
            "compatibility with ancestors is undeterminable.",
            evidence=make_evidence(file="README.md", field="license",
                                   expected="a license present in license-terms-v1", actual=declared),
        ))

    notice_in_release = _has_notice(snap)
    checked = sorted(set(ancestors) | set(lineage))
    for anc in checked:
        node = lineage.get(anc) or {}
        anc_lic = node.get("license")
        anc_lic = anc_lic.lower() if isinstance(anc_lic, str) else None
        depth = node.get("depth")
        where = f" (depth {depth})" if depth else ""
        if anc_lic is None or anc_lic not in table:
            out.append(finding(
                "V3", "license_unknown", "low",
                f"Ancestor '{anc}'{where} license '{anc_lic}' is unresolved/undeterminable; "
                "compatibility cannot be asserted.",
                evidence=make_evidence(field="base_model", expected="resolved ancestor license", actual=anc_lic),
                subject=anc,
            ))
            continue
        entry = table[anc_lic]
        allowed = entry.get("derivative_may_declare", [])
        if declared_known and declared not in allowed:
            out.append(finding(
                "V3", "license_incompatible", "high",
                f"Declared license '{declared}' is not permitted by ancestor '{anc}'{where} ({anc_lic}).",
                evidence=make_evidence(file="README.md", field="license",
                                       expected=f"one of {allowed}", actual=declared),
                subject=anc,
            ))
        if entry.get("requires_notice") and node.get("notice_present_in_ancestor") and not notice_in_release:
            out.append(finding(
                "V3", "attribution_missing", "medium",
                f"Ancestor '{anc}'{where} ({anc_lic}) requires attribution/NOTICE, but the release ships none.",
                evidence=make_evidence(field="files", expected="NOTICE/ATTRIBUTION artifact", actual="absent"),
                subject=anc,
            ))
    return out


# ===========================================================================
# V4 — Mandatory documentation gaps
# ===========================================================================

def _doc_signals(snap) -> dict:
    claims = _claims(snap)
    return {
        "config_present": snap.get("config") is not None,
        "model_index_present": bool(snap.get("model_index")),
        "license_present": claims.get("license") is not None,
        "param_present": claims.get("param_count") is not None,
    }


def _norm_text(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _deplural(s: str) -> str:
    return re.sub(r"(\w)s\b", r"\1", s)


def v4_doc_gaps(snap, ctx) -> list:
    out = []
    card = snap.get("card") or {}
    yaml = card.get("yaml") or {}
    signals = _doc_signals(snap)

    gpai = (ctx.packs.get("gpai-eu-v3") or ctx.packs.get("gpai-eu-v2")
            or ctx.packs.get("gpai-eu-v1") or {})
    # v3 uses content-word patterns over sentence windows (D-24); v1/v2 use
    # fixed-phrase keywords (legacy, kept for reproducibility).
    use_patterns = any("patterns" in it for it in gpai.get("items", []))
    if use_patterns:
        win = _tm.windows(card.get("prose") or "")
    else:
        np = _norm_text(card.get("prose") or "")
        npd = _deplural(np)

    for item in gpai.get("items", []):
        satisfied = any(signals.get(c) for c in item.get("satisfied_if", []))
        # Provider-document items (D-22): satisfied by a substantive card phrase
        # OR a reference/location field — a bare word does not satisfy.
        if not satisfied and item.get("provider_doc"):
            for f in item.get("yaml_fields", []):
                if yaml.get(f) not in (None, "", [], {}):
                    satisfied = True
                    break
        if not satisfied and use_patterns:
            satisfied = _tm.any_pattern(item.get("patterns", []), win)
        elif not satisfied:
            for kw in item.get("keywords", []):
                k = _norm_text(kw)
                if k and (k in np or _deplural(k) in npd):
                    satisfied = True
                    break
        if not satisfied:
            out.append(finding(
                "V4", "doc_gap", item.get("severity", "medium"),
                f"Missing required documentation: {item['label']} ({item['source']}).",
                evidence=make_evidence(file="README.md", field=item["id"],
                                       expected=item["label"], actual="absent"),
            ))

    hub = ctx.packs.get("hub-metadata-v1", {})
    has_base = bool(_claims(snap).get("base_model"))
    for spec in hub.get("required", []):
        if spec["field"] not in yaml or yaml.get(spec["field"]) in (None, "", []):
            out.append(finding(
                "V4", "doc_gap", spec.get("severity", "medium"),
                f"Missing required card field: {spec['label']}.",
                evidence=make_evidence(file="README.md", field=spec["field"],
                                       expected="present", actual="absent"),
            ))
    return out


# ===========================================================================
# V5 — Staleness / revision drift
# ===========================================================================

def _parse_date(s):
    if not isinstance(s, str):
        return None
    m = _DATE_RE.search(s)
    return m.group(0) if m else None


def v5_staleness(snap, ctx) -> list:
    out = []
    source = snap.get("source") or {}
    rev = source.get("revision")
    yaml = (snap.get("card") or {}).get("yaml") or {}

    # revision drift (card field)
    card_rev = yaml.get("revision") or yaml.get("checkpoint")
    if rev and isinstance(card_rev, str) and card_rev != rev:
        out.append(finding(
            "V5", "revision_drift", "medium",
            f"Card names revision '{card_rev}' but the release is pinned at '{rev}'.",
            evidence=make_evidence(file="README.md", field="revision", expected=rev, actual=card_rev),
        ))

    # model-index / result source drift
    for entry in (snap.get("model_index") or []):
        for res in (entry.get("results") or []) if isinstance(entry, dict) else []:
            src_rev = res.get("source_revision") or res.get("revision")
            if rev and isinstance(src_rev, str) and src_rev != rev:
                out.append(finding(
                    "V5", "revision_drift", "medium",
                    f"An evaluation result records source revision '{src_rev}', not the pinned '{rev}'.",
                    evidence=make_evidence(file="README.md", field="model-index.source_revision",
                                           expected=rev, actual=src_rev),
                ))

    # result-file recorded source checkpoint/revision drift (D-18 #8)
    for path, data in sorted((snap.get("result_files") or {}).items()):
        if not isinstance(data, dict):
            continue
        for k in ("source_checkpoint", "source_revision", "checkpoint", "revision"):
            v = data.get(k)
            if rev and isinstance(v, str) and v != rev:
                out.append(finding(
                    "V5", "revision_drift", "medium",
                    f"Result file '{path}' records source {k} '{v}', not the pinned '{rev}'.",
                    evidence=make_evidence(file=path, field=k, expected=rev, actual=v),
                ))
                break

    # stale as-of date
    as_of_now = ctx.as_of_now or snap.get("captured_at")
    now_d = _parse_date(as_of_now)
    as_of = _parse_date(yaml.get("as_of")) or _parse_date(yaml.get("valid_until"))
    if as_of and now_d and as_of < now_d:
        out.append(finding(
            "V5", "stale_as_of", "low",
            f"Declared 'as of' date {as_of} precedes the reference date {now_d}.",
            evidence=make_evidence(file="README.md", field="as_of", expected=f">= {now_d}", actual=as_of),
        ))
    return out


# ===========================================================================
# V6 — Evaluation claim inconsistency
# ===========================================================================

def _model_index_results(snap) -> list:
    """Return list of (benchmark_lower, metric_lower, value)."""
    out = []
    for entry in (snap.get("model_index") or []):
        if not isinstance(entry, dict):
            continue
        for res in entry.get("results") or []:
            task = (res.get("dataset") or {}).get("name") or (res.get("task") or {}).get("name") \
                or (res.get("task") or {}).get("type") or res.get("name")
            for metric in res.get("metrics") or []:
                if not isinstance(metric, dict):
                    continue
                name = metric.get("name") or metric.get("type")
                val = metric.get("value")
                if task and isinstance(val, (int, float)):
                    out.append((str(task).lower(), str(name or "").lower(), float(val)))
    return out


def _result_file_results(snap) -> list:
    out = []
    for _path, data in sorted((snap.get("result_files") or {}).items()):
        results = data.get("results") if isinstance(data, dict) else None
        if isinstance(results, dict):
            for bench, metrics in results.items():
                if isinstance(metrics, dict):
                    for mname, val in metrics.items():
                        if isinstance(val, (int, float)):
                            out.append((str(bench).lower(), str(mname).lower(), float(val)))
    return out


def v6_eval_consistency(snap, ctx) -> list:
    out = []
    mi = _model_index_results(snap)
    rf = _result_file_results(snap)

    # internal conflict within model-index
    seen = {}
    for bench, metric, val in mi:
        key = (bench, metric)
        if key in seen and abs(seen[key] - val) > 1e-9:
            out.append(finding(
                "V6", "eval_internal_conflict", "medium",
                f"Benchmark '{bench}' metric '{metric}' has conflicting values {seen[key]} and {val} in the card.",
                evidence=make_evidence(file="README.md", field="model-index",
                                       expected=seen[key], actual=val),
            ))
        else:
            seen[key] = val

    # model-index vs result files
    rf_map = {(b, m): v for b, m, v in rf}
    for key, val in seen.items():
        if key in rf_map and abs(rf_map[key] - val) > 1e-9:
            out.append(finding(
                "V6", "eval_value_mismatch", "medium",
                f"Benchmark '{key[0]}' metric '{key[1]}' is {val} in the card but {rf_map[key]} in a result file.",
                evidence=make_evidence(field="model-index vs result file",
                                       expected=val, actual=rf_map[key]),
            ))

    # prose claims: if the benchmark is ALSO in a structured record, compare the
    # VALUES (scale-aware, D-26) — a contradiction fires even though the benchmark
    # is "sourced"; a scale-only difference (0-1 vs 0-100) that agrees is silent.
    # If the benchmark is nowhere structured, it is an unsourced claim.
    prose = (snap.get("card") or {}).get("prose") or ""
    struct_vals = {}  # benchmark -> set of values normalised to a 0-100 scale
    for b, _m, v in mi + rf:
        struct_vals.setdefault(b, set()).add(v * 100.0 if abs(v) <= 1.0 else v)
    eval_claims = _claims(snap).get("eval_claims") or []
    for ec in eval_claims:  # structured card claims count as sourced too
        bm, val = ec.get("benchmark"), ec.get("value")
        if isinstance(bm, str) and isinstance(val, (int, float)):
            struct_vals.setdefault(bm.lower(), set()).add(val * 100.0 if abs(val) <= 1.0 else val)

    seen_claims = set()
    for bench_raw, val, raw in _prose_eval_claims(prose):
        bench = bench_raw.strip().lower()
        if (bench, raw) in seen_claims:
            continue
        seen_claims.add((bench, raw))
        try:
            pv = float(val)
        except (TypeError, ValueError):
            continue
        pv100 = pv * 100.0 if abs(pv) <= 1.0 else pv
        if bench in struct_vals:
            if all(abs(pv100 - sv) > 2.0 for sv in struct_vals[bench]):
                ref = sorted(struct_vals[bench])
                out.append(finding(
                    "V6", "eval_value_mismatch", "medium",
                    f"Prose reports {val} on '{bench_raw.strip()}' but the structured record(s) give "
                    f"{', '.join(f'{x:g}' for x in ref)} (on a 0-100 scale).",
                    evidence=make_evidence(file="README.md", field="prose vs structured",
                                           expected=ref[0], actual=pv100),
                ))
        else:
            out.append(finding(
                "V6", "unsourced_claim", "low",
                f"Prose reports a result for '{bench_raw.strip()}' ({val}) with no structured source.",
                evidence=make_evidence(file="README.md", field="prose",
                                       expected="a model-index / result-file entry", actual=raw),
            ))
    return out


# Terms that are hyperparameters / training-curve values, not benchmark claims.
_EVAL_STOPWORDS = {
    "note", "notes", "warning", "version", "example", "seed", "epoch", "epochs",
    "batch", "batch_size", "batch size", "lr", "learning_rate", "learning rate",
    "num_gpus", "gpus", "gpu", "tpu", "steps", "step", "warmup", "weight_decay",
    "dropout", "temperature", "top_p", "top_k", "max_length", "max_new_tokens",
    "beam", "beams", "loss", "training loss", "validation loss", "train loss",
    "val loss", "lr_scheduler", "num_epochs", "gradient_accumulation",
}
_NAT_CLAIM_RE = re.compile(
    r"(?i)(?:achiev\w*|scor\w*|reach\w*|obtain\w*|attain\w*|get\w*|yield\w*)\s+"
    r"(?:an?\s+|a\s+score\s+of\s+|up\s+to\s+)?(\d{1,3}(?:\.\d+)?)\s*%?\s+on\s+(?:the\s+)?"
    r"([A-Za-z][A-Za-z0-9][\w\-]{0,19})"
)


def _prose_eval_claims(prose: str):
    """Yield (benchmark, value, raw_match) for prose that reports a score,
    skipping hyperparameters / training-curve values."""
    out = []
    for m in _PROSE_CLAIM_RE.finditer(prose):
        bench = m.group("bench").strip()
        if bench.lower() in _EVAL_STOPWORDS:
            continue
        out.append((bench, m.group("val"), m.group(0).strip()))
    for m in _NAT_CLAIM_RE.finditer(prose):
        bench = m.group(2).strip()
        if bench.lower() in _EVAL_STOPWORDS:
            continue
        out.append((bench, m.group(1), m.group(0).strip()))
    return out


# ===========================================================================
# V7 — Release completeness
# ===========================================================================

_TOKENIZER_FILES = ("tokenizer.json", "tokenizer.model", "vocab.json", "spiece.model",
                    "spm.model", "sentencepiece.bpe.model", "vocab.txt", "merges.txt")


def v7_completeness(snap, ctx) -> list:
    out = []
    basenames = _basenames(snap)
    claims = _claims(snap)
    tok_cfg = snap.get("tokenizer_config")

    if isinstance(tok_cfg, dict):
        if not any(t in basenames for t in _TOKENIZER_FILES):
            out.append(finding(
                "V7", "tokenizer_missing", "high",
                "tokenizer_config.json is present but no tokenizer vocab/model file is in the release.",
                evidence=make_evidence(file="tokenizer_config.json",
                                       expected="a tokenizer vocab/model file", actual="absent"),
            ))

    # chat template expected for chat/instruct models
    yaml = (snap.get("card") or {}).get("yaml") or {}
    tags = [str(t).lower() for t in (yaml.get("tags") or [])]
    repo = str((snap.get("source") or {}).get("repo_id") or "")
    name_hint = (repo + " " + " ".join(tags)).lower()
    is_chat = ("conversational" in tags or "chat" in tags or "instruct" in name_hint
               or "chat" in name_hint)
    if is_chat and not (snap.get("chat_template")):
        out.append(finding(
            "V7", "chat_template_missing", "medium",
            "Release presents as an instruct/chat model but has no chat template.",
            evidence=make_evidence(file="tokenizer_config.json", field="chat_template",
                                   expected="a chat template", actual="absent"),
        ))

    # tokenizer_config references a chat-template file that is not in the release (D-18 #9)
    if isinstance(tok_cfg, dict):
        tmpl_file = tok_cfg.get("chat_template_file")
        if isinstance(tmpl_file, str) and tmpl_file.rsplit("/", 1)[-1] not in basenames:
            out.append(finding(
                "V7", "chat_template_file_missing", "medium",
                f"tokenizer_config references chat-template file '{tmpl_file}', which is absent from the release.",
                evidence=make_evidence(file="tokenizer_config.json", field="chat_template_file",
                                       expected=tmpl_file, actual="absent"),
            ))

    # generation config references ids beyond vocab
    gen = snap.get("generation_config")
    config = snap.get("config") or {}
    vocab = config.get("vocab_size")
    if isinstance(gen, dict) and isinstance(vocab, int) and vocab > 0:
        for key in ("eos_token_id", "bos_token_id", "pad_token_id"):
            val = gen.get(key)
            ids = val if isinstance(val, list) else [val]
            for tid in ids:
                if isinstance(tid, int) and tid >= vocab:
                    out.append(finding(
                        "V7", "genconfig_inconsistent", "medium",
                        f"generation_config {key}={tid} is outside the vocabulary size {vocab}.",
                        evidence=make_evidence(file="generation_config.json", field=key,
                                               expected=f"< {vocab}", actual=tid),
                    ))
                    break

    # safetensors index shard-count consistency
    sti = snap.get("safetensors_index")
    if isinstance(sti, dict):
        wm = sti.get("weight_map") or {}
        referenced = set(wm.values())
        shard_files = {b for b in basenames if b.endswith(".safetensors")}
        # shards declared by naming convention model-XXXXX-of-YYYYY
        expected_total = None
        for shard in referenced:
            m = re.search(r"-of-(\d{3,5})\.safetensors$", shard)
            if m:
                expected_total = int(m.group(1))
                break
        if expected_total is not None and len(shard_files) != expected_total:
            out.append(finding(
                "V7", "index_incomplete", "high",
                f"safetensors index implies {expected_total} shards but {len(shard_files)} are present.",
                evidence=make_evidence(file="model.safetensors.index.json", field="weight_map",
                                       expected=expected_total, actual=len(shard_files)),
            ))
    return out


# ===========================================================================
# V8 — Undeclared derivation (signal only, heuristic)
# ===========================================================================

def v8_undeclared_derivation(snap, ctx) -> list:
    out = []
    claims = _claims(snap)
    if claims.get("base_model"):
        return out  # a base is declared; nothing undeclared
    fp_pack = ctx.packs.get("fingerprints-v1", {})
    fields = tuple(fp_pack.get("fields", DEFAULT_FIELDS))
    known = fp_pack.get("known_bases", {})
    fp = fingerprint(snap.get("config"), fields)
    if fp and fp in known:
        out.append(finding(
            "V8", "undeclared_derivation", "info",
            f"Config fingerprint closely matches known base '{known[fp]}' but no base_model is declared.",
            heuristic=True,
            evidence=make_evidence(file="config.json", field="(fingerprint)",
                                   expected="a declared base_model", actual=known[fp]),
        ))
    return out


ALL_CHECKS = [
    v1_artifact_record,
    v2_arch_scale,
    v3_license_lineage,
    v4_doc_gaps,
    v5_staleness,
    v6_eval_consistency,
    v7_completeness,
    v8_undeclared_derivation,
]
