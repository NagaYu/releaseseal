"""F-1 regression — unified SHA-256 alg-label canonicalization (D-44/D-46).

A genuine ``bom_hash_mismatch`` must fire — and a matching hash must compare
clean, never ``unverifiable`` — for every SHA-256 label spelling that the shared
``_norm_alg`` rule canonicalizes, in both CycloneDX and SPDX. A label that
canonicalizes to no known algorithm stays ``unverifiable`` (no invented finding).
"""
import pytest

from releaseseal.bom import import_bom, verify_bom

HASH_A = "92fd8db60f8d544c2519c0c5506c5a23ae4d2932da6508f03e9e295ac26f6d2d"
HASH_B = "0" * 64
# The report's four CycloneDX labels: canonical + the three sloppy spellings.
SLOPPY = ["SHA-256", " SHA-256", "SHA-256 ", "SHA_256"]


def _cdx(alg, content, name="model.safetensors"):
    return {"bomFormat": "CycloneDX", "specVersion": "1.6", "components": [
        {"bom-ref": "f", "type": "machine-learning-model", "name": name,
         "hashes": [{"alg": alg, "content": content}]}]}


def _spdx(alg, content, name="model.safetensors"):
    return {"@context": "https://spdx.org/rdf/3.0.0/spdx-context.jsonld", "@graph": [
        {"spdxId": "spdx:m", "type": "software_Package", "name": name, "versionInfo": "1",
         "hasDeclaredLicense": "apache-2.0", "typeOfModel": "transformer",
         "verifiedUsing": [{"type": "Hash", "algorithm": alg, "hashValue": content}]}]}


def _art(sha):
    return {"files": [{"path": "model.safetensors", "sha256": sha}], "license": None}


def _hash_unverifiable(result):
    return any(u["claim"] == "hash" for u in result["unverifiable"])


def _fired(result):
    return any(f["code"] == "bom_hash_mismatch" for f in result["findings"])


@pytest.mark.parametrize("alg", SLOPPY)
def test_cdx_mismatch_fires(alg):
    r = verify_bom(import_bom(_cdx(alg, HASH_A)), _art(HASH_B))
    assert _fired(r)
    assert not _hash_unverifiable(r)


@pytest.mark.parametrize("alg", SLOPPY)
def test_cdx_match_compared_clean(alg):
    r = verify_bom(import_bom(_cdx(alg, HASH_A)), _art(HASH_A))
    assert not _fired(r)
    assert not _hash_unverifiable(r)  # decided clean, not dropped to unverifiable


@pytest.mark.parametrize("alg", SLOPPY)
def test_cdx_spdx_parity_mismatch(alg):
    rc = verify_bom(import_bom(_cdx(alg, HASH_A)), _art(HASH_B))
    rs = verify_bom(import_bom(_spdx(alg, HASH_A)), _art(HASH_B))
    assert _fired(rc) and _fired(rs)  # same label -> same verdict in both formats


@pytest.mark.parametrize("alg", SLOPPY)
def test_cdx_spdx_parity_match(alg):
    rc = verify_bom(import_bom(_cdx(alg, HASH_A)), _art(HASH_A))
    rs = verify_bom(import_bom(_spdx(alg, HASH_A)), _art(HASH_A))
    assert not _fired(rc) and not _fired(rs)
    assert not _hash_unverifiable(rc) and not _hash_unverifiable(rs)


@pytest.mark.parametrize("alg", ["SHA-512", "sha3-256", "SHA-1", "md5", "blake2b"])
def test_unknown_alg_stays_unverifiable(alg):
    r = verify_bom(import_bom(_cdx(alg, HASH_A)), _art(HASH_B))
    assert not _fired(r)             # no invented finding for an unknown algorithm
    assert _hash_unverifiable(r)
