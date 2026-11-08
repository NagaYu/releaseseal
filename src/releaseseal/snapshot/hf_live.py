"""Live HF fetcher — used ONLY by the optional smoke step, never by tests.

Imported lazily; the default test run and CLI verify path never touch the
network. Metadata + small files only (no weight downloads).
"""
from __future__ import annotations

import json
import urllib.request
from typing import Optional

_BASE = "https://huggingface.co"
_UA = "releaseseal-smoke/0.1 (metadata-only)"  # generic client name, no user email


class HttpFetcher:
    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    def _get(self, url: str) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
            return resp.read().decode("utf-8")

    def model_info(self, repo: str, revision: Optional[str]) -> dict:
        url = f"{_BASE}/api/models/{repo}"
        if revision:
            url += f"?revision={revision}"
        return json.loads(self._get(url))

    def tree(self, repo: str, revision: Optional[str]) -> list:
        rev = revision or "main"
        url = f"{_BASE}/api/models/{repo}/tree/{rev}?recursive=true"
        return json.loads(self._get(url))

    def file_text(self, repo: str, revision: Optional[str], path: str) -> Optional[str]:
        rev = revision or "main"
        url = f"{_BASE}/{repo}/resolve/{rev}/{path}"
        try:
            return self._get(url)
        except Exception:
            return None
