"""Bench Part A-D — synthetic dataset-release generator (SPEC.md §E1.7).

Builds small synthetic dataset releases as ``dsnapshot/1`` objects directly (tiny
data files' content inlined via the shared ``dsample/1``; no directories), with
planted W1–W7 violations and near-miss cleans. Fully seeded: same seed ->
identical bytes (tested). Mirrors the Part A conventions of §6 exactly (marker
discipline = class ids only; scorer counts non-heuristic, non-info findings).
"""
from __future__ import annotations

import hashlib
import json
import random

from .. import BENCH_MANIFEST_D_SCHEMA, DSAMPLE_SEED
from ..canonical import canonical_sha256
from ..rules import load_pack
from ..snapshot.dsample import build_sample
from ..snapshot.dschema import finalize, make_dcard, make_dsnapshot, make_dsource

CLASSES = ("W1", "W2", "W3", "W4", "W5", "W6", "W7")

# Distinct, digit-free, @-free English sentences (each ~12–18 words) so rows
# classify as `en` and stay far from near-duplicate without any detector hits.
_POOL = [
    "the research corpus collects freely licensed articles about natural science and public history",
    "volunteers transcribed old community newsletters describing local gardening clubs and seasonal harvest festivals",
    "the collection gathers open recipes for soups stews and baked bread from many regions",
    "linguists annotated spoken interviews about childhood memories and favourite summer holidays by the sea",
    "the dataset summarises public lectures on astronomy ocean currents and migratory bird behaviour",
    "editors compiled short reviews of classic novels plays and translated poetry for study",
    "the archive preserves letters between travelling merchants discussing trade routes and mountain weather",
    "teachers shared lesson plans covering fractions geometry and the water cycle for young learners",
    "the corpus documents folk tales about clever foxes patient turtles and singing rivers",
    "journalists donated feature stories on urban parks farmers markets and neighbourhood libraries",
    "the collection records oral histories of railway workers lighthouse keepers and orchard farmers",
    "scholars catalogued descriptions of medieval maps ancient coins and painted ceramic bowls",
    "the dataset includes gentle guides to birdwatching stargazing and pressing wildflowers",
    "contributors wrote plain explanations of photosynthesis tides and the phases of the moon",
    "the archive holds transcripts of town meetings about bridges bicycle lanes and tree planting",
    "curators gathered captions for museum exhibits on pottery weaving and glass blowing",
    "the corpus features travel diaries from walking tours across quiet valleys and coastal villages",
    "students collected proverbs about patience friendship and the changing colours of autumn leaves",
    "the collection describes community kitchens teaching soups preserves and simple seasonal salads",
    "naturalists logged sightings of hedgehogs barn owls and otters near the slow winding brook",
    "the dataset compiles interviews with potters bakers and bookbinders about their daily craft",
    "writers submitted essays on gardening without chemicals composting and sharing surplus vegetables",
    "the archive gathers programmes from amateur orchestras choirs and village theatre productions",
    "researchers summarised studies of coral reefs kelp forests and the creatures that shelter there",
    "the corpus keeps guides to repairing bicycles mending clothes and restoring wooden chairs",
    "historians transcribed ledgers from old mills bakeries and family run grocery shops",
    "the collection records lullabies counting songs and playground rhymes from many languages",
    "botanists wrote notes on ferns mosses and the quiet lichens that cling to shaded stones",
    "the dataset offers introductions to pottery glazing beekeeping and small scale cheese making",
    "editors assembled columns about public transport libraries and free lectures for curious readers",
    "the archive preserves recipes for herbal teas fruit jams and slow roasted root vegetables",
    "guides explained how comets form why seasons change and how rainbows appear after rain",
    "the corpus features accounts of long walks through birch forests over hills and along shores",
    "volunteers described restoring canals planting hedgerows and welcoming swifts back each spring",
    "the collection documents workshops on calligraphy paper folding and natural plant dyeing",
    "reporters wrote about reopening a cinema repairing a clock tower and painting a mural downtown",
    "the dataset includes careful summaries of weather patterns river levels and gentle coastal winds",
    "apprentices recorded lessons in blacksmithing stone carving and the patient art of thatching",
    "the archive gathers notes on migrating whales nesting terns and the tides of the northern bay",
    "neighbours shared stories about shared gardens mended fences and long evenings telling tales",
]


def _hex64(rng: random.Random) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(64))


def _jsonl_bytes(rows: list) -> str:
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows)


def _make_files(rows_by_split: dict) -> list:
    files = [{"path": "README.md", "size": 512, "sha256": hashlib.sha256(b"readme").hexdigest(),
              "hash_source": "streamed"},
             {"path": "LICENSE", "size": 128, "sha256": hashlib.sha256(b"license").hexdigest(),
              "hash_source": "streamed"}]
    for name in sorted(rows_by_split):
        text = _jsonl_bytes(rows_by_split[name])
        files.append({"path": f"{name}.jsonl", "size": len(text.encode("utf-8")),
                      "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      "hash_source": "streamed"})
    files.sort(key=lambda f: f["path"])
    return files


# Split layout: train 6, validation 3, test 3 (12 rows total).
_SPLIT_SIZES = (("train", 6), ("validation", 3), ("test", 3))


def _build_clean_d(rng: random.Random, name: str, *, profile: str = "plain") -> dict:
    base = rng.randrange(len(_POOL))
    rows_by_split = {}
    k = 0
    for split, n in _SPLIT_SIZES:
        rows = []
        for _ in range(n):
            rows.append({"text": _POOL[(base + k) % len(_POOL)]})
            k += 1
        rows_by_split[split] = rows

    license_ = "apache-2.0"
    sources = [{"name": "public-web-corpus", "license": "apache-2.0"}]
    decon = ["benchsuite-alpha"]  # declared & honoured (rows don't contaminate)

    if profile == "unusual_license":
        license_ = "cc-by-sa-4.0"
        sources = [{"name": "wiki-mirror", "license": "cc-by-sa-4.0"}]
    elif profile == "multi_source":
        sources = [{"name": "corpus-a", "license": "apache-2.0"},
                   {"name": "corpus-b", "license": "mit"}]  # mit permits apache-2.0
    elif profile == "contamination_undeclared":
        # Embed a suite item but do NOT declare decontamination -> info only.
        item = load_pack("contamination-v1")["suites"][0]["items"][7]
        rows_by_split["train"][0] = {"text": item}
        decon = []

    pii = "present" if profile == "pii_present" else "none"

    file_inventory = [{"path": f"{s}.jsonl", "rows": n} for s, n in _SPLIT_SIZES]
    annotations = {
        "pii": pii,
        "dedup_rate": 0.0,
        "sources": sources,
        "file_inventory": file_inventory,
        "decontaminated_against": decon,
    }
    yaml = {"license": license_, "language": ["en"], "annotations": annotations}
    card = make_dcard(yaml=yaml)  # declarations extracted deterministically

    croissant = {"license": license_,
                 "distribution": [{"name": f"{s}.jsonl", "contentUrl": f"{s}.jsonl",
                                   "sha256": _hex64(rng)} for s, _ in _SPLIT_SIZES],
                 "recordSet": [{"name": "default"}]}

    files = _make_files(rows_by_split)
    sample = build_sample(rows_by_split, seed=DSAMPLE_SEED)
    splits = [{"name": s, "num_rows": n,
               "num_bytes": len(_jsonl_bytes(rows_by_split[s]).encode("utf-8"))}
              for s, n in _SPLIT_SIZES]

    snap = make_dsnapshot(
        captured_at="2026-11-11",
        source=make_dsource("local_dataset", repo_id=f"bench/{name}", path=f"/bench/{name}"),
        files=files,
        card=card,
        croissant=croissant,
        splits=splits,
        sample=sample,
    )
    return snap


# Note: for bench snapshots the row content lives only in the sample record, so
# the content mutators (W4–W7) edit ``snap['sample']['rows']`` directly.

# --- PII tokens for W4 (valid, detector-triggering; masked in findings) -----
_PII_TOKENS = [
    ("card_luhn", "4111111111111111"),
    ("iban_mod97", "GB82WEST12345698765432"),
    ("email", "alice.smith@example.org"),
    ("ipv4", "203.0.113.45"),
    ("secret_aws", "AKIAIOSFODNN7EXAMPLE"),
    ("secret_github", "ghp_abcdefghijklmnopqrstuvwxyz0123456789"),
    ("secret_openai", "sk-abcdefghijklmnopqrstuvwxyz0123"),
]


def _mutate_w1(snap, variant, rng):
    decl = snap["card"]["declarations"]
    if variant % 2 == 0:  # croissant disagreement
        snap["croissant"]["license"] = "mit"           # declared stays apache-2.0
    else:  # declared license unknown to the table
        decl["license"] = "weird-custom-1.0"
        snap["croissant"]["license"] = "weird-custom-1.0"  # agree -> only unknown fires
        decl["sources"] = []                                # avoid W2 interaction


def _mutate_w2(snap, variant, rng):
    decl = snap["card"]["declarations"]
    if variant % 2 == 0:  # incompatible source license
        decl["sources"] = [{"name": "nc-corpus", "license": "cc-by-nc-4.0"}]
    else:  # source license unknown to the table
        decl["sources"] = [{"name": "mystery-corpus", "license": "mystery-1.0"}]


def _mutate_w3(snap, variant, rng):
    decl = snap["card"]["declarations"]
    v = variant % 3
    if v == 0:  # declared_file_missing
        decl["file_inventory"].append({"path": "extra-shard.jsonl", "rows": None})
    elif v == 1:  # undeclared_data_file
        snap["files"].append({"path": "surprise.jsonl", "size": 10,
                              "sha256": _hex64(rng), "hash_source": "streamed"})
        snap["files"].sort(key=lambda f: f["path"])
    else:  # row_count_mismatch
        decl["file_inventory"][0]["rows"] = decl["file_inventory"][0]["rows"] + 10


def _mutate_w4(snap, variant, rng):
    det_id, token = _PII_TOKENS[variant % len(_PII_TOKENS)]
    rows = snap["sample"]["rows"]
    rows[0]["text"] = rows[0]["text"] + " reference token " + token
    # pii already "none" in the base -> pii_claim_falsified (high)


def _mutate_w5(snap, variant, rng):
    suites = load_pack("contamination-v1")["suites"]
    suite = suites[variant % 2]
    item = suite["items"][(variant * 3) % len(suite["items"])]
    snap["sample"]["rows"][0]["text"] = item
    snap["card"]["declarations"]["decontaminated_against"] = [suite["suite_id"]]


def _mutate_w6(snap, variant, rng):
    dup = _POOL[(variant * 2) % len(_POOL)]
    for r in snap["sample"]["rows"]:
        if r["split"] == "train":
            r["text"] = dup                       # 6 identical train rows -> ~0.5 measured
    snap["card"]["declarations"]["dedup_rate"] = 0.02  # declared honest-looking but false


def _mutate_w7(snap, variant, rng):
    decl = snap["card"]["declarations"]
    if variant % 2 == 0:  # share mismatch (rows are 100% en, declared 50/50)
        decl["languages"] = ["en", "ja"]
        decl["language_shares"] = {"en": 0.5, "ja": 0.5}
    else:  # declared language absent (ja declared, rows are en)
        decl["languages"] = ["ja"]
        decl["language_shares"] = {}


_MUTATORS = {
    "W1": _mutate_w1, "W2": _mutate_w2, "W3": _mutate_w3, "W4": _mutate_w4,
    "W5": _mutate_w5, "W6": _mutate_w6, "W7": _mutate_w7,
}

_CLEAN_PROFILES = ["plain", "pii_present", "unusual_license",
                   "contamination_undeclared", "multi_source", "plain"]


def generate(seed: int = DSAMPLE_SEED, per_class: int = 12, n_clean: int = 36) -> dict:
    rng = random.Random(seed)
    cases = []
    idx = 0
    for cls in CLASSES:
        for i in range(per_class):
            idx += 1
            snap = _build_clean_d(rng, f"dcase-{idx:04d}", profile="plain")
            _MUTATORS[cls](snap, i, rng)
            cases.append({
                "id": f"dcase-{idx:04d}",
                "kind": cls,
                "expected": [cls],
                "snapshot": finalize(snap),
            })
    for i in range(n_clean):
        idx += 1
        profile = _CLEAN_PROFILES[i % len(_CLEAN_PROFILES)]
        snap = _build_clean_d(rng, f"dcase-{idx:04d}", profile=profile)
        cases.append({
            "id": f"dcase-{idx:04d}",
            "kind": "clean",
            "expected": [],
            "snapshot": finalize(snap),
        })

    composition = {cls: per_class for cls in CLASSES}
    composition["clean"] = n_clean
    return {
        "schema_version": BENCH_MANIFEST_D_SCHEMA,
        "seed": seed,
        "cases_sha256": canonical_sha256(cases),
        "composition": composition,
        "cases": cases,
    }
