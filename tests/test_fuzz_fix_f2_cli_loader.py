"""F-2 regression — the CLI file-load contract (D-47).

Every ``_load_json`` subcommand must turn an unreadable input file (malformed,
truncated, empty, non-JSON, trailing garbage, wrong encoding, missing) into
``error: ...`` on stderr + exit 2, never an uncaught traceback.
"""
import json

import pytest

from releaseseal.cli import CliError, _load_json, main

_GOOD = json.dumps({
    "bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
    "metadata": {"component": {"bom-ref": "rel@1", "type": "machine-learning-model",
                               "name": "m", "version": "1"}},
    "components": [{"bom-ref": "f", "type": "file", "name": "model.safetensors",
                   "hashes": [{"alg": "SHA-256", "content": "0" * 64}]}]})

# The report's seven CLI triggers.
TRIGGERS = {
    "truncated-open-array": '{"bomFormat":"CycloneDX","specVersion":"1.6","components":[',
    "truncated-mid": _GOOD[: len(_GOOD) // 2],
    "empty-file": "",
    "not-json": "this is not json at all \x00\x01",
    "trailing-garbage": _GOOD + " )))garbage",
    "lonely-brace": "{",
    "utf16": "﻿\x00{bad",  # leading UTF-8 BOM + NUL
}


def _write(tmp_path, payload):
    p = tmp_path / "in.json"
    p.write_text(payload, encoding="utf-8", errors="surrogatepass")
    return p


@pytest.mark.parametrize("name,payload", list(TRIGGERS.items()))
def test_cli_bom_import_trigger_exit2_no_traceback(tmp_path, capsys, name, payload):
    rc = main(["bom", "import", str(_write(tmp_path, payload)),
               "-o", str(tmp_path / "out.json")])
    err = capsys.readouterr().err
    assert rc == 2, name
    assert err.startswith("error:"), (name, err)
    assert "Traceback (most recent call last)" not in err, name


def test_cli_bom_import_missing_file_exit2(tmp_path, capsys):
    rc = main(["bom", "import", str(tmp_path / "does_not_exist.json"),
               "-o", str(tmp_path / "out.json")])
    err = capsys.readouterr().err
    assert rc == 2
    assert err.startswith("error:")
    assert "Traceback (most recent call last)" not in err


@pytest.mark.parametrize("payload", list(TRIGGERS.values()) + ["123trailing", "{bad"])
def test_load_json_raises_clierror(tmp_path, payload):
    p = _write(tmp_path, payload)
    with pytest.raises(CliError):
        _load_json(str(p))


def test_load_json_missing_file_raises_clierror(tmp_path):
    with pytest.raises(CliError):
        _load_json(str(tmp_path / "nope.json"))


def test_contract_applies_to_other_subcommand(tmp_path, capsys):
    """`_load_json` is shared; a different subcommand (verify) is equally hardened."""
    p = _write(tmp_path, "{ truncated")
    rc = main(["verify", str(p)])
    err = capsys.readouterr().err
    assert rc == 2
    assert err.startswith("error:")
    assert "Traceback (most recent call last)" not in err
