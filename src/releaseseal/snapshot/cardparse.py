"""Model-card parsing: YAML front-matter (minimal subset) + claim extraction.

Design is stdlib-only (no PyYAML). The ``hf`` adapter does not use the YAML
parser (HF API returns ``cardData`` already parsed); only the ``local`` adapter
and tests parse README front-matter, whose format we control. The subset
supported: ``key: value`` scalars, nested maps by indentation, block lists
(``- item``), inline flow lists ``[a, b]`` and maps ``{k: v}``. Documented limits
in SPEC/DECISIONS; unparseable front-matter yields ``{}`` + a note, never a crash.
"""
from __future__ import annotations

import re
from typing import Any

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.DOTALL)


def split_front_matter(text: str) -> tuple[str, str]:
    """Return (front_matter_yaml, prose). No front matter -> ("", text)."""
    m = _FM_RE.match(text.lstrip("﻿"))
    if not m:
        return "", text
    return m.group(1), m.group(2)


# --- minimal YAML ----------------------------------------------------------

def _scalar(tok: str) -> Any:
    t = tok.strip()
    if t == "" or t in ("~", "null", "None"):
        return None
    if (t[0] == '"' and t[-1] == '"') or (t[0] == "'" and t[-1] == "'"):
        return t[1:-1]
    low = t.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if re.fullmatch(r"-?\d+", t):
        try:
            return int(t)
        except ValueError:
            return t
    if re.fullmatch(r"-?\d+\.\d+", t):
        return float(t)
    return t


def _parse_flow(tok: str) -> Any:
    t = tok.strip()
    if t.startswith("[") and t.endswith("]"):
        inner = t[1:-1].strip()
        if not inner:
            return []
        return [_scalar(x) for x in _split_flow(inner)]
    if t.startswith("{") and t.endswith("}"):
        inner = t[1:-1].strip()
        out: dict[str, Any] = {}
        if inner:
            for part in _split_flow(inner):
                if ":" in part:
                    k, v = part.split(":", 1)
                    out[k.strip()] = _scalar(v)
        return out
    return _scalar(t)


def _split_flow(s: str) -> list[str]:
    """Split a flow collection body on commas not nested in [] or {}."""
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return parts


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def parse_yaml(text: str) -> Any:
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    value, _ = _parse_block(lines, 0, 0)
    return value if value is not None else {}


def _parse_block(lines: list[str], i: int, indent: int) -> tuple[Any, int]:
    if i >= len(lines):
        return None, i
    first = lines[i]
    if first.lstrip().startswith("- "):
        return _parse_list(lines, i, indent)
    return _parse_map(lines, i, indent)


def _parse_map(lines: list[str], i: int, indent: int) -> tuple[dict, int]:
    out: dict[str, Any] = {}
    while i < len(lines):
        line = lines[i]
        ind = _indent(line)
        if ind < indent:
            break
        if ind > indent:  # defensive: unexpected deeper line
            break
        content = line.strip()
        if content.startswith("- "):
            break
        if ":" not in content:
            i += 1
            continue
        key, _, rest = content.partition(":")
        key = key.strip()
        rest = rest.strip()
        if rest == "":
            # nested block (map or list) or empty
            if i + 1 < len(lines) and _indent(lines[i + 1]) > ind:
                child_indent = _indent(lines[i + 1])
                val, i = _parse_block(lines, i + 1, child_indent)
                out[key] = val
            else:
                out[key] = None
                i += 1
        else:
            out[key] = _parse_flow(rest)
            i += 1
    return out, i


def _parse_list(lines: list[str], i: int, indent: int) -> tuple[list, int]:
    out: list[Any] = []
    while i < len(lines):
        line = lines[i]
        ind = _indent(line)
        if ind < indent or not line.strip().startswith("- "):
            break
        item = line.strip()[2:].strip()
        if item == "":
            if i + 1 < len(lines) and _indent(lines[i + 1]) > ind:
                val, i = _parse_block(lines, i + 1, _indent(lines[i + 1]))
                out.append(val)
            else:
                out.append(None)
                i += 1
        elif ":" in item and not (item.startswith("[") or item.startswith("{")):
            # list of maps: treat the "- k: v" line as the first map entry
            synth = [" " * (ind + 2) + item]
            j = i + 1
            while j < len(lines) and _indent(lines[j]) > ind:
                synth.append(lines[j])
                j += 1
            val, _ = _parse_map(synth, 0, ind + 2)
            out.append(val)
            i = j
        else:
            out.append(_parse_flow(item))
            i += 1
    return out, i


def parse_front_matter(text: str) -> tuple[dict, str]:
    fm, prose = split_front_matter(text)
    if not fm.strip():
        return {}, prose
    try:
        data = parse_yaml(fm)
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    return data, prose


# --- claim extraction ------------------------------------------------------

_PARAM_RE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*([bBmM])(?![a-zA-Z])")
# A prose parameter count must sit in a PARAMETER context (D-17 #2) so that an
# incidental "<digits>B/M" anywhere in the text is not misread as this model's
# parameter count. Real Part B examples (see partb.md Errata): the "623b" that
# was mis-read for t5-small is the prefix of an image-URL hash
# (camo.githubusercontent.com/623b4dea…), NOT a token count; "Yi-34B" is a
# sibling model's name. Requiring an adjacent param/model/llm token excludes both.
_PARAM_CTX = [
    re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*([bBmM])\b[\s\-]*param", re.IGNORECASE),
    re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*([bBmM])\b[\s\-]+(?:model|llm)\b", re.IGNORECASE),
    re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(billion|million)\s+param", re.IGNORECASE),
    re.compile(r"param[\w\s:()\-]{0,12}?(?<![\w.])(\d+(?:\.\d+)?)\s*([bBmM])\b", re.IGNORECASE),
]
_CTX_RE = re.compile(
    r"(?:context(?:\s*(?:length|window))?|max(?:imum)?\s*(?:sequence|context)\s*length)"
    r"[^\d]{0,20}?([\d,]{3,})(\s*[kK])?",
    re.IGNORECASE,
)


def _norm_license(val) -> Any:
    if isinstance(val, str):
        return val.strip().lower()
    if isinstance(val, list) and val and isinstance(val[0], str):
        return val[0].strip().lower()
    return None


def _unit_mult(unit: str) -> int:
    u = unit.lower()
    if u in ("b", "billion"):
        return 1_000_000_000
    return 1_000_000  # m / million


def extract_param_count(yaml: dict, prose: str) -> tuple[Any, Any]:
    """Return (param_count:int|None, source_text:str|None).

    Structured card fields first; otherwise a prose number is accepted only in a
    parameter context (D-17 #2), never a bare "<N>B/M" anywhere in the text.
    """
    for key in ("params", "parameters", "num_parameters", "parameter_count"):
        if isinstance(yaml.get(key), int):
            return yaml[key], f"{key}: {yaml[key]}"
    for rx in _PARAM_CTX:
        m = rx.search(prose)
        if m:
            return int(round(float(m.group(1)) * _unit_mult(m.group(2)))), m.group(0).strip()
    return None, None


def extract_context_length(yaml: dict, prose: str) -> Any:
    for key in ("context_length", "max_position_embeddings", "context_window"):
        if isinstance(yaml.get(key), int):
            return yaml[key]
    m = _CTX_RE.search(prose)
    if m:
        digits = int(m.group(1).replace(",", ""))
        if m.group(2):  # trailing k/K
            digits *= 1000
        return digits
    return None


def _as_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return [x for x in v if x is not None]
    return [v]


def extract_claims(yaml: dict, prose: str) -> dict:
    from .schema import empty_claims

    claims = empty_claims()
    pc, pct = extract_param_count(yaml, prose)
    claims["param_count"] = pc
    claims["param_count_text"] = pct
    claims["context_length"] = extract_context_length(yaml, prose)
    arch = yaml.get("architecture") or yaml.get("arch")
    claims["architecture"] = arch if isinstance(arch, str) else None
    claims["license"] = _norm_license(yaml.get("license"))
    claims["base_model"] = [str(x) for x in _as_list(yaml.get("base_model"))]
    rel = yaml.get("base_model_relation")
    claims["base_model_relation"] = rel if isinstance(rel, str) else None
    claims["eval_claims"] = []  # headline prose eval claims extracted by V6 as needed
    return claims
