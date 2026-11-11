"""Checked-in builders for the generated rule packs (SPEC.md §E1.4, §E1.5).

The committed JSON files (`packs/contamination-v1.json`, `packs/lid-v1.json`) are
the source of truth; these builders regenerate them **byte-identically** (tested
in `tests/test_rules_d.py`). Both are dependency-free and deterministic.

Run ``python -m releaseseal.rules.build_packs`` to (re)write the committed files.
"""
from __future__ import annotations

import json
import math
import os

from ..canonical import canonical_sha256

_PACKS_DIR = os.path.join(os.path.dirname(__file__), "packs")
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_FIXTURES_DIR = os.path.join(_ROOT, "fixtures", "contamination")


def serialize(pack: dict) -> str:
    """The canonical committed form: sorted keys, 2-space indent, UTF-8, trailing NL."""
    return json.dumps(pack, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


# ===========================================================================
# contamination-v1 — two synthetic 40-item benchmark suites (§E1.4)
# ===========================================================================

_SUBJECTS = [
    "the independent evaluation team", "a careful graduate student",
    "our deterministic scoring harness", "the offline benchmark committee",
    "a reproducible research pipeline", "the sealed holdout authors",
    "an automated grading routine", "the curated question bank",
]
_VERBS = [
    "carefully recorded answers to", "systematically compared responses on",
    "thoroughly analyzed the solutions for", "precisely measured accuracy across",
    "methodically verified completions for", "exhaustively checked reasoning over",
]
_TOPICS = [
    "the multiple choice reasoning questions", "the grade school arithmetic word problems",
    "the natural language inference pairs", "the reading comprehension passages",
    "the commonsense physical interaction prompts", "the scientific fact verification items",
    "the code completion exercises", "the open domain trivia challenges",
]
_TAILS = [
    "under a single fixed random seed during the controlled offline experiment",
    "without any network access across repeated fully deterministic evaluation trials",
    "while logging every intermediate score into the audit evidence record",
    "using only the pinned snapshot content that the specification describes",
]


def _suite_items(suite: str) -> list:
    items = []
    for i in range(40):
        s = _SUBJECTS[i % len(_SUBJECTS)]
        v = _VERBS[(i // 1) % len(_VERBS)]
        t = _TOPICS[(i // 2) % len(_TOPICS)]
        tail = _TAILS[(i // 3) % len(_TAILS)]
        items.append(f"{s} {v} {t} {tail} for {suite} item number {i:02d}")
    return items


# --- Real benchmark suites as 13-gram hashes (Phase-E2, §E1.4, D-38) --------
#
# Real public benchmark suites are stored ONLY as the sha256 hashes of their
# normalized word 13-grams (W5 normalization, D-32) — never raw benchmark text.
# The hashes are computed by the checked-in builder from a pinned source
# snapshot cached under fixtures/contamination/ (the "source of truth" for the
# real-suite part). Fetching is a one-time, offline-of-tests step
# (``python -m releaseseal.rules.build_packs fetch``); the test suite and
# ``build_contamination_pack()`` only READ the cached fixtures, so regeneration
# is byte-identical without the network.

_REAL_SUITE_SPECS = [
    {"suite_id": "gsm8k-test", "repo": "openai/gsm8k", "config": "main",
     "split": "test", "text_fields": ["question"], "max_rows": 1500},
    {"suite_id": "squad-validation", "repo": "rajpurkar/squad", "config": "plain_text",
     "split": "validation", "text_fields": ["context"], "max_rows": 3000},
]


def _fixture_path(suite_id: str) -> str:
    return os.path.join(_FIXTURES_DIR, f"{suite_id}.json")


def _load_real_fixture(suite_id: str):
    path = _fixture_path(suite_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _ngram_hash_suite_from_fixture(fix: dict) -> dict:
    """Deterministically build an ngram-hashes suite from a cached source
    snapshot. Hashes use the single W5 helper (D-32/D-38); stored sorted so the
    committed pack is byte-stable regardless of item order."""
    from ..verify.wchecks import ngram_hash_set
    hashes = set()
    for item in fix.get("items", []):
        hashes |= ngram_hash_set(item, 13)
    ordered = sorted(hashes)
    return {
        "suite_id": fix["suite_id"],
        "kind": "ngram-hashes",
        "source_repo": fix["source_repo"],
        "source_revision": fix["source_revision"],
        "source_config": fix.get("source_config"),
        "source_split": fix.get("source_split"),
        "text_fields": fix.get("text_fields"),
        "item_count": fix.get("item_count", len(fix.get("items", []))),
        "ngram_count": len(ordered),
        "ngram_hashes_sha256": canonical_sha256(ordered),
        "ngram_hashes": ordered,
    }


def build_contamination_pack() -> dict:
    suites = []
    for suite_id in ("benchsuite-alpha", "benchsuite-beta"):
        items = _suite_items(suite_id)
        suites.append({
            "suite_id": suite_id,
            "items_sha256": canonical_sha256(items),
            "items": items,
        })
    # Real suites, appended in pinned order where a cached source snapshot
    # exists. A missing fixture is simply absent (reported as not-run), never
    # fabricated. Suites with zero 13-grams are dropped (nothing to match).
    for spec in _REAL_SUITE_SPECS:
        fix = _load_real_fixture(spec["suite_id"])
        if not fix:
            continue
        suite = _ngram_hash_suite_from_fixture(fix)
        if suite["ngram_count"] == 0:
            continue
        suites.append(suite)
    return {
        "pack_id": "contamination-v1",
        "version": "1.1.0",
        "source": "ReleaseSeal contamination suites (§E1.4). Synthetic suites benchsuite-alpha/beta are seeded templates (items). Real suites (kind=ngram-hashes) store only sha256 hashes of normalized word 13-grams of pinned public benchmarks (gsm8k-test, squad-validation) — never raw benchmark text — built from cached source snapshots under fixtures/contamination/ (D-38).",
        "suites": suites,
    }


# --- One-time real-suite fetch (network; never run by tests) ----------------

def _http_get_json(url: str, timeout: float = 30.0) -> dict:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "releaseseal-build/0.1 (metadata-only)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _dataset_revision(repo: str):
    info = _http_get_json(f"https://huggingface.co/api/datasets/{repo}")
    return info.get("sha")


def _fetch_rows(repo: str, config: str, split: str, text_fields, max_rows: int):
    """Fetch up to ``max_rows`` rows via the HF datasets-server rows endpoint,
    returning the deduped (first-seen order) joined text_field values."""
    seen, items, offset = set(), [], 0
    while offset < max_rows:
        length = min(100, max_rows - offset)
        url = (f"https://datasets-server.huggingface.co/rows?dataset={repo}"
               f"&config={config}&split={split}&offset={offset}&length={length}")
        data = _http_get_json(url)
        batch = data.get("rows") or []
        if not batch:
            break
        for rr in batch:
            row = rr.get("row") or {}
            parts = [str(row[f]) for f in text_fields if isinstance(row.get(f), str)]
            text = " ".join(parts).strip()
            if text and text not in seen:
                seen.add(text)
                items.append(text)
        offset += length
        if len(batch) < length:
            break
    return items, offset


def fetch_real_suites() -> None:
    """Fetch each real suite once and cache a pinned source snapshot under
    fixtures/contamination/. Records the dataset revision + item counts. A suite
    that cannot be fetched is skipped (reported as not-run), never fabricated."""
    os.makedirs(_FIXTURES_DIR, exist_ok=True)
    for spec in _REAL_SUITE_SPECS:
        sid = spec["suite_id"]
        try:
            rev = _dataset_revision(spec["repo"])
            items, fetched = _fetch_rows(spec["repo"], spec["config"], spec["split"],
                                         spec["text_fields"], spec["max_rows"])
        except Exception as e:  # noqa: BLE001
            print(f"NOT-RUN {sid}: {type(e).__name__}: {e}")
            continue
        fix = {
            "suite_id": sid,
            "source_repo": spec["repo"],
            "source_revision": rev,
            "source_config": spec["config"],
            "source_split": spec["split"],
            "text_fields": spec["text_fields"],
            "max_rows": spec["max_rows"],
            "fetched_rows": fetched,
            "item_count": len(items),
            "items": items,
        }
        with open(_fixture_path(sid), "w", encoding="utf-8") as fh:
            json.dump(fix, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
        print(f"cached {sid}: rev={rev} items={len(items)} (from {fetched} rows)")


# ===========================================================================
# lid-v1 — dependency-free character n-gram language ID (§E1.5)
# ===========================================================================

# Short seed paragraphs per language (public-domain-style, composed for this
# purpose). Distinct vocabulary/scripts give well-separated char n-gram profiles.
SEED_TEXTS = {
    "en": (
        "The small language model was trained on a mixture of public web text and "
        "freely licensed books. Researchers evaluated the system carefully and reported "
        "the results so that anyone could reproduce the numbers without special access."
    ),
    "es": (
        "El modelo de lenguaje fue entrenado con una mezcla de textos públicos de la web "
        "y libros con licencia libre. Los investigadores evaluaron el sistema con cuidado "
        "y publicaron los resultados para que cualquiera pudiera reproducir las cifras."
    ),
    "fr": (
        "Le modèle de langage a été entraîné sur un mélange de textes publics du web et "
        "de livres sous licence libre. Les chercheurs ont évalué le système avec soin et "
        "ont publié les résultats afin que chacun puisse reproduire les chiffres obtenus."
    ),
    "de": (
        "Das kleine Sprachmodell wurde mit einer Mischung aus öffentlichen Webtexten und "
        "frei lizenzierten Büchern trainiert. Die Forscher bewerteten das System sorgfältig "
        "und veröffentlichten die Ergebnisse, damit jeder die Zahlen nachvollziehen konnte."
    ),
    "ja": (
        "この小さな言語モデルは、公開されたウェブテキストと自由に利用できる書籍を混ぜたデータで"
        "学習されました。研究者たちは注意深く評価を行い、誰でも数値を再現できるように結果を公開しました。"
    ),
    "zh": (
        "这个小型语言模型是在公开的网络文本和自由许可的书籍混合数据上训练的。研究人员仔细地评估了"
        "该系统，并公开了结果，以便任何人都可以在不需要特殊权限的情况下复现这些数字。"
    ),
}

_FLOOR_LOGPROB = round(math.log(1e-6), 6)
_MARGIN = 1.0


def _char_ngrams(text: str):
    t = " ".join(text.lower().split())
    for n in (3, 4, 5):
        for i in range(len(t) - n + 1):
            yield t[i:i + n]


def build_lid_pack() -> dict:
    profiles = {}
    for code, text in SEED_TEXTS.items():
        counts = {}
        total = 0
        for g in _char_ngrams(text):
            counts[g] = counts.get(g, 0) + 1
            total += 1
        prof = {g: round(math.log(c / total), 6) for g, c in counts.items()}
        profiles[code] = prof
    return {
        "pack_id": "lid-v1",
        "version": "1.0.0",
        "source": "ReleaseSeal dependency-free language-ID profiles (character 3/4/5-gram log-likelihood over composed seed paragraphs; §E1.5). No external model.",
        "languages": sorted(SEED_TEXTS.keys()),
        "floor_logprob": _FLOOR_LOGPROB,
        "margin": _MARGIN,
        "profiles": profiles,
    }


# ===========================================================================

_BUILDERS = {
    "contamination-v1": build_contamination_pack,
    "lid-v1": build_lid_pack,
}


def write_all() -> None:
    for pack_id, builder in _BUILDERS.items():
        path = os.path.join(_PACKS_DIR, f"{pack_id}.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(serialize(builder()))
        print(f"wrote {path}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        fetch_real_suites()  # one-time network fetch of the real-suite sources
    write_all()
