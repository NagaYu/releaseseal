"""Content-word text matching for V4 (DECISIONS.md D-24).

Replaces fixed-phrase / substring matching with order-independent co-occurrence
of *content-word stems* within a window (a card section). Uses a Porter stemmer
so plurals and inflections are handled properly (modalities -> modal, not a naive
trailing-s strip); function words do not affect matching.
"""
from __future__ import annotations

import re
from functools import lru_cache

# Function words ignored in matching (articles, prepositions, conjunctions,
# pronouns, auxiliaries). Content words such as "model", "use", "data" are kept.
FUNCTION_WORDS = frozenset("""
a an the of to in on for and or with by is are was were be been being as at it
its this that these those we our you your they their them he she i from into over
under per via than then so such which who whom whose each any all both not no do
does did has have had will would can could may might shall should must about there
here also using used but if while when where what how why into onto off up down
only very more most some many few other another same between during per across
""".split())

_WORD_RE = re.compile(r"[a-z0-9]+")


# ---------------------------------------------------------------------------
# Porter stemmer (Martin Porter's algorithm; compact, deterministic)
# ---------------------------------------------------------------------------
_VOWELS = "aeiou"


def _is_consonant(w, i):
    c = w[i]
    if c in _VOWELS:
        return False
    if c == "y":
        return True if i == 0 else not _is_consonant(w, i - 1)
    return True


def _measure(stem):
    n = 0
    prev_v = False
    for i in range(len(stem)):
        v = not _is_consonant(stem, i)
        if prev_v and not v:
            n += 1
        prev_v = v
    return n


def _contains_vowel(stem):
    return any(not _is_consonant(stem, i) for i in range(len(stem)))


def _double_consonant_end(w):
    return len(w) >= 2 and w[-1] == w[-2] and _is_consonant(w, len(w) - 1)


def _cvc(w):
    if len(w) < 3:
        return False
    if _is_consonant(w, len(w) - 1) and not _is_consonant(w, len(w) - 2) and _is_consonant(w, len(w) - 3):
        return w[-1] not in "wxy"
    return False


@lru_cache(maxsize=20000)
def porter(word: str) -> str:
    w = word.lower()
    if len(w) <= 2:
        return w

    # Step 1a
    if w.endswith("sses"):
        w = w[:-2]
    elif w.endswith("ies"):
        w = w[:-2]
    elif w.endswith("ss"):
        pass
    elif w.endswith("s"):
        w = w[:-1]

    # Step 1b
    step1b_second = False
    if w.endswith("eed"):
        if _measure(w[:-3]) > 0:
            w = w[:-1]
    elif w.endswith("ed"):
        if _contains_vowel(w[:-2]):
            w = w[:-2]; step1b_second = True
    elif w.endswith("ing"):
        if _contains_vowel(w[:-3]):
            w = w[:-3]; step1b_second = True
    if step1b_second:
        if w.endswith(("at", "bl", "iz")):
            w = w + "e"
        elif _double_consonant_end(w) and not w.endswith(("l", "s", "z")):
            w = w[:-1]
        elif _measure(w) == 1 and _cvc(w):
            w = w + "e"

    # Step 1c
    if w.endswith("y") and _contains_vowel(w[:-1]):
        w = w[:-1] + "i"

    # Step 2
    step2 = {"ational": "ate", "tional": "tion", "enci": "ence", "anci": "ance",
             "izer": "ize", "abli": "able", "alli": "al", "entli": "ent", "eli": "e",
             "ousli": "ous", "ization": "ize", "ation": "ate", "ator": "ate",
             "alism": "al", "iveness": "ive", "fulness": "ful", "ousness": "ous",
             "aliti": "al", "iviti": "ive", "biliti": "ble"}
    for suf, rep in step2.items():
        if w.endswith(suf):
            if _measure(w[:-len(suf)]) > 0:
                w = w[:-len(suf)] + rep
            break

    # Step 3
    step3 = {"icate": "ic", "ative": "", "alize": "al", "iciti": "ic", "ical": "ic",
             "ful": "", "ness": ""}
    for suf, rep in step3.items():
        if w.endswith(suf):
            if _measure(w[:-len(suf)]) > 0:
                w = w[:-len(suf)] + rep
            break

    # Step 4
    step4 = ["al", "ance", "ence", "er", "ic", "able", "ible", "ant", "ement",
             "ment", "ent", "ou", "ism", "ate", "iti", "ous", "ive", "ize"]
    for suf in step4:
        if w.endswith(suf):
            stem = w[:-len(suf)]
            if _measure(stem) > 1:
                w = stem
            break
    else:
        if w.endswith("ion") and _measure(w[:-3]) > 1 and w[-4:-3] in ("s", "t"):
            w = w[:-3]

    # Step 5a
    if w.endswith("e"):
        stem = w[:-1]
        if _measure(stem) > 1 or (_measure(stem) == 1 and not _cvc(stem)):
            w = stem
    # Step 5b
    if _measure(w) > 1 and _double_consonant_end(w) and w.endswith("l"):
        w = w[:-1]
    return w


def stems(text: str):
    """Ordered content-word stems of ``text`` (function words removed)."""
    out = []
    for tok in _WORD_RE.findall(text.lower()):
        if tok in FUNCTION_WORDS:
            continue
        out.append(porter(tok))
    return out


_SENT_SPLIT = re.compile(r"(?<=[.!?;:])\s+")


def windows(prose: str):
    """Split prose into sentence/heading windows; return a list of stem-sets.

    A window is one sentence (or a heading line). Co-occurrence is required
    *within* a window, so content words that merely appear in different sentences
    of the card do not jointly satisfy a pattern — this keeps a dropped section
    from leaking through words reused elsewhere.
    """
    win = []
    for line in (prose or "").splitlines():
        line = line.strip().lstrip("#").strip()
        if not line:
            continue
        for sent in _SENT_SPLIT.split(line):
            s = set(stems(sent))
            if s:
                win.append(s)
    return win


def pattern_satisfied(pattern, win_sets) -> bool:
    """True if some window contains the stems of every word in ``pattern``."""
    want = {porter(w.lower()) for w in pattern}
    return any(want <= ws for ws in win_sets)


def any_pattern(patterns, win_sets) -> bool:
    return any(pattern_satisfied(p, win_sets) for p in patterns)
