"""Dataset verification checks W1–W8 (SPEC.md §E1.3, extension design §3.3).

Each check is ``(dsnapshot, ctx) -> list[finding]``. Pure and deterministic. W1–W7
are gate-counted (when severity != info); W8 is heuristic/info and never counted.
All claim surfaces are the closed-vocabulary ``card.declarations`` — no prose
parsing anywhere (design hard rule). PII/secret values appear only masked (D-31).
"""
from __future__ import annotations

import hashlib
import random
import re

from . import lid
from .findings import finding, make_evidence

# Packs the dataset profile loads (reuses license-terms-v1 unchanged).
DATASET_PACK_IDS = ("dataset-hub-v1", "contamination-v1", "lid-v1", "license-terms-v1")

_DATA_EXTS = (".jsonl", ".csv", ".parquet", ".txt", ".json")
_DATA_ROW_EXTS = (".jsonl", ".csv")


# --- small accessors -------------------------------------------------------

def _decl(snap) -> dict:
    return (snap.get("card") or {}).get("declarations") or {}


def _rows(snap) -> list:
    return (snap.get("sample") or {}).get("rows") or []


def _file_paths(snap) -> set:
    return {f.get("path") for f in (snap.get("files") or []) if f.get("path")}


# --- normalization & n-grams (W5/W6; pinned §E1.3) -------------------------

_WS_RE = re.compile(r"\s+")
_NON_RE = re.compile(r"[^a-z0-9 ]+")


def normalize_words(s: str) -> list:
    s = s.lower()
    s = _WS_RE.sub(" ", s)
    s = _NON_RE.sub("", s)  # delete non-[a-z0-9 ] characters
    return [w for w in s.split(" ") if w]


def _ngrams(words: list, n: int) -> set:
    if len(words) < n:
        return set()
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def ngram_hash_set(text: str, n: int = 13) -> set:
    """sha256 hex of each normalized word n-gram of ``text`` (pinned W5
    normalization, D-32). The single source of truth shared by W5's
    ngram-hashes suite leg and the ``contamination-v1`` builder (§E1.4 Phase-E2):
    a 13-gram hashes as sha256 of the gram's words joined by a single space.
    """
    return {hashlib.sha256(" ".join(g).encode("utf-8")).hexdigest()
            for g in _ngrams(normalize_words(text), n)}


# --- PII detectors (W4; ids pinned §E1.3) ----------------------------------

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_IPV4_RE = re.compile(r"(?<!\d)(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?!\d)")
_AWS_RE = re.compile(r"AKIA[0-9A-Z]{16}")
_GITHUB_RE = re.compile(r"ghp_[A-Za-z0-9]{36}")
_OPENAI_RE = re.compile(r"sk-[A-Za-z0-9]{20,}")
_DIGIT_RUN_RE = re.compile(r"(?<!\d)\d{13,19}(?!\d)")
_IBAN_RE = re.compile(r"(?<![A-Z0-9])([A-Z]{2}\d{2}[A-Z0-9]{11,30})(?![A-Z0-9])")


def _luhn_ok(num: str) -> bool:
    total, alt = 0, False
    for ch in reversed(num):
        d = ord(ch) - 48
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _iban_ok(s: str) -> bool:
    rearranged = s[4:] + s[:4]
    try:
        conv = "".join(str(int(c, 36)) for c in rearranged)
        return int(conv) % 97 == 1
    except ValueError:
        return False


def _detect_luhn(text):
    for m in _DIGIT_RUN_RE.finditer(text):
        if _luhn_ok(m.group(0)):
            return m.group(0)
    return None


def _detect_iban(text):
    for m in _IBAN_RE.finditer(text):
        if _iban_ok(m.group(1)):
            return m.group(1)
    return None


def _detect_ipv4(text):
    for m in _IPV4_RE.finditer(text):
        if all(0 <= int(o) <= 255 for o in m.group(1).split(".")):
            return m.group(1)
    return None


def _first(rx):
    def f(text):
        m = rx.search(text)
        return m.group(0) if m else None
    return f


# Ordered so findings are deterministic per (detector, row).
_DETECTORS = [
    ("card_luhn", _detect_luhn),
    ("iban_mod97", _detect_iban),
    ("email", _first(_EMAIL_RE)),
    ("ipv4", _detect_ipv4),
    ("secret_aws", _first(_AWS_RE)),
    ("secret_github", _first(_GITHUB_RE)),
    ("secret_openai", _first(_OPENAI_RE)),
]


def mask(value: str) -> str:
    """Mask a detected value to first-2 + last-2 (D-31); short values fully."""
    if len(value) <= 4:
        return "•" * len(value)
    return value[:2] + "•" * (len(value) - 4) + value[-2:]


# --- MinHash (W6; construction pinned §E1.3) -------------------------------

_P = (1 << 61) - 1


def _minhash_coeffs():
    rng = random.Random(20261111)
    return [(rng.randrange(1, _P), rng.randrange(0, _P)) for _ in range(128)]


_COEFFS = _minhash_coeffs()


def _shingles(words: list) -> set:
    if len(words) < 5:
        return set()
    return {tuple(words[i:i + 5]) for i in range(len(words) - 4)}


def _signature(shingles: set):
    if not shingles:
        return None
    bases = [int.from_bytes(hashlib.blake2b(" ".join(sh).encode("utf-8"), digest_size=8).digest(), "big") % _P
             for sh in shingles]
    return tuple(min((a * h + b) % _P for h in bases) for a, b in _COEFFS)


# ===========================================================================
# W1 — License consistency
# ===========================================================================

def normalize_license_text(text: str) -> str:
    """Normalize LICENSE text for file identification (pinned, dataset-hub-v1):
    lowercase -> drop any line containing 'copyright' or '(c)' -> collapse all
    whitespace runs to a single space -> strip. Phrases match as substrings of
    the resulting single-line text.
    """
    lowered = (text or "").lower()
    kept = [ln for ln in lowered.splitlines() if "copyright" not in ln and "(c)" not in ln]
    return _WS_RE.sub(" ", " ".join(kept)).strip()


def identify_license_file(text: str, pack: dict):
    """Identify a license id from normalized LICENSE text using the pinned
    phrase table + evaluation order (dataset-hub-v1 1.1.0). First match in
    ``license_file_order`` wins: ALL ``required`` substrings present and NONE
    of ``forbidden``. Returns the license id or None (never guesses — D-29/E2).
    """
    phrases = (pack or {}).get("license_file_phrases") or {}
    order = (pack or {}).get("license_file_order") or list(phrases.keys())
    norm = normalize_license_text(text)
    if not norm:
        return None
    for lic_id in order:
        spec = phrases.get(lic_id)
        if not spec:
            continue
        required = spec.get("required") or []
        forbidden = spec.get("forbidden") or []
        if required and all(p in norm for p in required) and not any(p in norm for p in forbidden):
            return lic_id
    return None


def w1_license_consistency(snap, ctx) -> list:
    out = []
    decl = _decl(snap)
    table = (ctx.packs.get("license-terms-v1") or {}).get("licenses", {})
    declared = decl.get("license")
    croissant = snap.get("croissant") or {}
    cro = croissant.get("license") if isinstance(croissant, dict) else None
    cro = cro.strip().lower() if isinstance(cro, str) else None
    # LICENSE-file identification leg (Phase-E2): identify the license from any
    # captured LICENSE file via dataset-hub-v1's phrase table. license-terms-v1
    # stays byte-unchanged (D-29); the identification data lives in dataset-hub-v1
    # (1.1.0, D-37). No LICENSE file / no identification -> leg silent (never guessed).
    dhub = ctx.packs.get("dataset-hub-v1") or {}
    file_lic = None
    for lf in snap.get("license_files") or []:
        if isinstance(lf, dict) and isinstance(lf.get("text"), str):
            ident = identify_license_file(lf["text"], dhub)
            if ident:
                file_lic = ident
                break  # first LICENSE file that identifies wins (files are path-sorted)

    present = [(src, val) for src, val in
               (("declared", declared), ("croissant", cro), ("license_file", file_lic)) if val]
    for i in range(len(present)):
        for j in range(i + 1, len(present)):
            (sa, a), (sb, b) = present[i], present[j]
            if a != b:
                out.append(finding(
                    "W1", "license_inconsistent", "high",
                    f"Declared license sources disagree: {sa}='{a}' vs {sb}='{b}'.",
                    evidence=make_evidence(field="license", expected=a, actual=b),
                ))
    if declared and declared not in table:
        out.append(finding(
            "W1", "license_unknown", "low",
            f"Declared dataset license '{declared}' is not in the license-terms table; "
            "compatibility is undeterminable.",
            evidence=make_evidence(file="README.md", field="license",
                                   expected="a license in license-terms-v1", actual=declared),
        ))
    return out


# ===========================================================================
# W2 — Declared source-license rollup
# ===========================================================================

def w2_source_rollup(snap, ctx) -> list:
    out = []
    decl = _decl(snap)
    table = (ctx.packs.get("license-terms-v1") or {}).get("licenses", {})
    declared = decl.get("license")
    for src in decl.get("sources") or []:
        name = src.get("name")
        lic = (src.get("license") or "").strip().lower()
        if not lic:
            continue
        if lic not in table:
            out.append(finding(
                "W2", "license_unknown", "low",
                f"Source '{name}' declares license '{lic}', unknown to the license-terms table.",
                evidence=make_evidence(field="sources", expected="a license in license-terms-v1", actual=lic),
                subject=name,
            ))
            continue
        allowed = table[lic].get("derivative_may_declare", [])
        if declared and declared not in allowed:
            out.append(finding(
                "W2", "source_license_incompatible", "high",
                f"Declared aggregate license '{declared}' is not permitted by source '{name}' ({lic}).",
                evidence=make_evidence(field="license", expected=f"one of {allowed}", actual=declared),
                subject=name,
            ))
    return out


# ===========================================================================
# W3 — Inventory truth
# ===========================================================================

def _split_of(path: str) -> str:
    base = path.rsplit("/", 1)[-1]
    for ext in _DATA_ROW_EXTS + (".parquet", ".txt", ".json"):
        if base.endswith(ext):
            return base[: -len(ext)]
    return base


def w3_inventory_truth(snap, ctx) -> list:
    out = []
    inv = _decl(snap).get("file_inventory") or []
    if not inv:
        return out  # W3 grades a declaration; none -> silent
    file_paths = _file_paths(snap)
    declared_paths = {it["path"] for it in inv}

    for it in inv:
        if it["path"] not in file_paths:
            out.append(finding(
                "W3", "declared_file_missing", "medium",
                f"Declared file '{it['path']}' is absent from the release.",
                evidence=make_evidence(field="file_inventory", expected=it["path"], actual="absent"),
            ))

    data_present = {p for p in file_paths if any(p.endswith(e) for e in _DATA_EXTS)}
    for p in sorted(data_present - declared_paths):
        out.append(finding(
            "W3", "undeclared_data_file", "medium",
            f"Data file '{p}' is present but not listed in the declared file inventory.",
            evidence=make_evidence(field="file_inventory", expected="declared", actual=p),
        ))

    split_rows = {s.get("name"): s.get("num_rows") for s in (snap.get("splits") or [])
                  if isinstance(s, dict)}
    for it in inv:
        rows = it.get("rows")
        if not isinstance(rows, int):
            continue
        actual = split_rows.get(_split_of(it["path"]))
        if isinstance(actual, int) and rows != actual:
            out.append(finding(
                "W3", "row_count_mismatch", "medium",
                f"Declared row count for '{it['path']}' is {rows} but the split holds {actual}.",
                evidence=make_evidence(field="file_inventory", expected=rows, actual=actual),
            ))
    return out


# ===========================================================================
# W4 — PII falsification
# ===========================================================================

def w4_pii(snap, ctx) -> list:
    out = []
    pii = _decl(snap).get("pii")
    for r in _rows(snap):
        text = r.get("text") or ""
        split = r.get("split")
        idx = r.get("index")
        for det_id, matcher in _DETECTORS:
            m = matcher(text)
            if not m:
                continue
            masked = mask(m)
            if pii == "none":
                code, sev = "pii_claim_falsified", "high"
                expected = "no PII (declared none)"
            else:
                code, sev = "pii_detected", "medium"
                expected = "PII present as declared"
            out.append(finding(
                "W4", code, sev,
                f"Detector '{det_id}' matched in sampled row (split '{split}', index {idx}); "
                f"declaration pii={pii!r}.",
                evidence=make_evidence(file=split, field="sample", expected=expected,
                                       actual=f"{masked} ({det_id})"),
            ))
    return out


# ===========================================================================
# W5 — Benchmark contamination (measured)
# ===========================================================================

def w5_contamination(snap, ctx) -> list:
    out = []
    pack = ctx.packs.get("contamination-v1") or {}
    rows = _rows(snap)
    total = len(rows)
    if not pack.get("suites") or total == 0:
        return out
    decon = set(_decl(snap).get("decontaminated_against") or [])
    # Both suite kinds compare on word-13-gram equality (D-32). For the plain
    # "items" suites we compare gram tuples; for "ngram-hashes" suites (real
    # benchmarks stored as sha256 of normalized 13-grams, never raw text) we
    # compare the rows' 13-gram hashes against the stored hash set.
    row_grams = [_ngrams(normalize_words(r.get("text") or ""), 13) for r in rows]
    row_hashes = None  # computed lazily only if a hashed suite is present
    for suite in pack["suites"]:
        sid = suite.get("suite_id")
        if suite.get("kind") == "ngram-hashes":
            suite_hashes = set(suite.get("ngram_hashes") or [])
            if not suite_hashes:
                continue
            if row_hashes is None:
                row_hashes = [{hashlib.sha256(" ".join(g).encode("utf-8")).hexdigest()
                               for g in gr} for gr in row_grams]
            contaminated = sum(1 for h in row_hashes if h & suite_hashes)
        else:
            suite_grams = set()
            for item in suite.get("items", []):
                suite_grams |= _ngrams(normalize_words(item), 13)
            if not suite_grams:
                continue
            contaminated = sum(1 for g in row_grams if g & suite_grams)
        rate = contaminated / total
        if rate <= 0:
            continue
        if sid in decon:
            out.append(finding(
                "W5", "decontamination_claim_falsified", "high",
                f"Suite '{sid}' is declared decontaminated-against but {contaminated}/{total} "
                f"sampled rows share a 13-gram with it (rate {rate:.3f}).",
                evidence=make_evidence(field="decontaminated_against",
                                       expected=f"0 overlap with {sid}", actual=f"{rate:.3f}"),
                subject=sid,
            ))
        else:
            out.append(finding(
                "W5", "contamination_measured", "info",
                f"Measured contamination against suite '{sid}': {contaminated}/{total} sampled "
                f"rows share a 13-gram (rate {rate:.3f}).",
                evidence=make_evidence(field="sample", expected=None, actual=f"{rate:.3f}"),
                subject=sid,
            ))
    return out


# ===========================================================================
# W6 — Dedup measurement
# ===========================================================================

def w6_dedup(snap, ctx) -> list:
    rows = _rows(snap)
    total = len(rows)
    if total == 0:
        return []
    sigs = [_signature(_shingles(normalize_words(r.get("text") or ""))) for r in rows]
    partner = [False] * total
    for i in range(total):
        if sigs[i] is None:
            continue
        for j in range(i + 1, total):
            if sigs[j] is None:
                continue
            matches = sum(1 for x, y in zip(sigs[i], sigs[j]) if x == y)
            if matches / 128 >= 0.8:
                partner[i] = True
                partner[j] = True
    measured = sum(partner) / total
    declared = _decl(snap).get("dedup_rate")
    if isinstance(declared, (int, float)) and abs(measured - declared) > 0.05:
        return [finding(
            "W6", "dedup_rate_mismatch", "medium",
            f"Measured near-duplicate rate {measured:.3f} diverges from the declared {declared:.3f} "
            "by more than 0.05.",
            evidence=make_evidence(field="dedup_rate", expected=f"{declared:.3f}", actual=f"{measured:.3f}"),
        )]
    return [finding(
        "W6", "dedup_measured", "info",
        f"Measured near-duplicate rate over the sample: {measured:.3f}.",
        evidence=make_evidence(field="sample", expected=None, actual=f"{measured:.3f}"),
    )]


# ===========================================================================
# W7 — Composition drift
# ===========================================================================

def w7_composition(snap, ctx) -> list:
    out = []
    decl = _decl(snap)
    declared = decl.get("languages") or []
    if not declared:
        return out
    pack = ctx.packs.get("lid-v1") or {}
    rows = _rows(snap)
    total = len(rows)
    if total == 0:
        return out
    counts = {}
    for r in rows:
        code = lid.classify(r.get("text") or "", pack)
        counts[code] = counts.get(code, 0) + 1
    share = {k: v / total for k, v in counts.items()}
    shares_decl = decl.get("language_shares") or {}

    if shares_decl:
        for code in declared:
            dshare = shares_decl.get(code, 0.0)
            mshare = share.get(code, 0.0)
            if abs(mshare - dshare) > 0.10:
                out.append(finding(
                    "W7", "language_share_mismatch", "medium",
                    f"Declared share of '{code}' is {dshare:.3f} but measured {mshare:.3f} "
                    "(divergence > 0.10).",
                    evidence=make_evidence(field="language_shares", expected=f"{dshare:.3f}", actual=f"{mshare:.3f}"),
                    subject=code,
                ))
    else:
        for code in declared:
            if share.get(code, 0.0) == 0.0:
                out.append(finding(
                    "W7", "declared_language_absent", "medium",
                    f"Declared language '{code}' has a measured share of 0 in the sample.",
                    evidence=make_evidence(field="languages", expected=f"share > 0 for {code}", actual="0.000"),
                    subject=code,
                ))
        for code, ms in sorted(share.items()):
            if code != "und" and code not in declared and ms >= 0.20:
                out.append(finding(
                    "W7", "undeclared_language_dominant", "medium",
                    f"Language '{code}' is {ms:.3f} of the sample but is not declared.",
                    evidence=make_evidence(field="languages", expected="declared", actual=f"{code} {ms:.3f}"),
                    subject=code,
                ))
    return out


# ===========================================================================
# W8 — Dataset-card completeness (signal only, heuristic)
# ===========================================================================

def w8_card_completeness(snap, ctx) -> list:
    out = []
    decl = _decl(snap)
    pack = ctx.packs.get("dataset-hub-v1") or {}
    for fld in pack.get("fields", []):
        val = decl.get(fld["field"])
        if val in (None, "", [], {}):
            out.append(finding(
                "W8", "card_field_missing", "info",
                f"Dataset card declaration missing: {fld['label']}.",
                heuristic=True,
                evidence=make_evidence(file="README.md", field=fld["id"],
                                       expected="present", actual="absent"),
            ))
    return out


ALL_W_CHECKS = [
    w1_license_consistency,
    w2_source_rollup,
    w3_inventory_truth,
    w4_pii,
    w5_contamination,
    w6_dedup,
    w7_composition,
    w8_card_completeness,
]
