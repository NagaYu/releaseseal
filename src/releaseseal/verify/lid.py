"""`lid-v1` language classifier (SPEC.md §E1.5) — dependency-free, deterministic.

Reads the pinned profile pack; no external model. Scoring: summed character
3/4/5-gram log-likelihood; ``und`` when the top language's margin over the
runner-up is below the pack's ``margin``.
"""
from __future__ import annotations


def _char_ngrams(text: str):
    t = " ".join(text.lower().split())
    for n in (3, 4, 5):
        for i in range(len(t) - n + 1):
            yield t[i:i + n]


def classify(text: str, pack: dict) -> str:
    """Return a language code from the pack's set, or ``und``."""
    profiles = pack.get("profiles") or {}
    floor = pack.get("floor_logprob", -13.815511)
    margin = pack.get("margin", 1.0)
    if not profiles or not isinstance(text, str) or not text.strip():
        return "und"
    grams = list(_char_ngrams(text))
    if not grams:
        return "und"
    scores = []
    for code, prof in profiles.items():
        s = 0.0
        for g in grams:
            s += prof.get(g, floor)
        scores.append((s, code))
    scores.sort(key=lambda sc: (-sc[0], sc[1]))
    if len(scores) == 1:
        return scores[0][1]
    top, second = scores[0], scores[1]
    if top[0] - second[0] < margin:
        return "und"
    return top[1]
