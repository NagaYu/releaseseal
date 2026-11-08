"""V8 config fingerprint (DECISIONS.md D-08)."""
from __future__ import annotations

from typing import Optional

from ..canonical import canonical_sha256

DEFAULT_FIELDS = (
    "model_type", "hidden_size", "num_hidden_layers", "num_attention_heads",
    "num_key_value_heads", "vocab_size", "intermediate_size",
)


def fingerprint(config: Optional[dict], fields=DEFAULT_FIELDS) -> Optional[str]:
    if not isinstance(config, dict):
        return None
    vals = {}
    for f in fields:
        if f in config and config[f] is not None:
            vals[f] = config[f]
    if "hidden_size" not in vals or "num_hidden_layers" not in vals:
        return None
    return canonical_sha256({"fields": list(fields), "values": vals})
