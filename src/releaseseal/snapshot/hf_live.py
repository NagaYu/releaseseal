"""Live HF fetcher — used ONLY by the optional smoke step, never by tests.

Imported lazily; the default test run and CLI verify path never touch the
network. Metadata + small files only (no weight downloads).
"""
from __future__ import annotations

import json
import urllib.error
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


_DS_SERVER = "https://datasets-server.huggingface.co"


class DatasetHttpFetcher:
    """Live dataset fetcher for the Part B-D audit (Phase-E2). Implements the
    ``DatasetFixtureFetcher`` interface the ``hf_dataset`` adapter calls, over the
    HF Hub API (metadata + small files) and the datasets-server rows endpoint
    (capped content sample). Metadata + capped samples only — NO bulk downloads,
    $0 spend. Every call is fail-soft: on any error it returns an empty result so
    one dataset never aborts the run (coverage is recorded by the caller).

    ``rows_per_split`` / ``max_splits`` bound the content sample; the chosen
    config and the per-config split totals are memoised per repo so ``splits``
    and ``rows`` agree. The adapter's ``dsample/1`` reservoir then runs over the
    fetched prefix; the true split totals (from /size) stay in ``splits`` so the
    recorded coverage (sampled / total) is honest.
    """

    def __init__(self, timeout: float = 30.0, rows_per_split: int = 200, max_splits: int = 2,
                 max_configs_tried: int = 4, min_interval: float = 0.4, max_retries: int = 4):
        self.timeout = timeout
        self.rows_per_split = rows_per_split
        self.max_splits = max_splits
        self.max_configs_tried = max_configs_tried
        self.min_interval = min_interval   # polite spacing between live calls
        self.max_retries = max_retries
        self._resolved: dict = {}          # repo -> {"splits": [...], "rows": {...}}
        self._last_call = 0.0

    def _get(self, url: str) -> str:
        import time
        last_exc = None
        for attempt in range(self.max_retries + 1):
            gap = self.min_interval - (time.monotonic() - self._last_call)
            if gap > 0:
                time.sleep(gap)
            self._last_call = time.monotonic()
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                    return resp.read().decode("utf-8")
            except urllib.error.HTTPError as e:  # retry on throttle / transient server error
                last_exc = e
                if e.code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    retry_after = e.headers.get("Retry-After") if e.headers else None
                    try:
                        wait = float(retry_after) if retry_after else 0.0
                    except ValueError:
                        wait = 0.0
                    time.sleep(max(wait, 1.0 * (2 ** attempt)))
                    continue
                raise
            except Exception as e:  # noqa: BLE001
                last_exc = e
                if attempt < self.max_retries:
                    time.sleep(1.0 * (2 ** attempt))
                    continue
                raise
        if last_exc:
            raise last_exc
        return ""

    def _get_json(self, url: str):
        return json.loads(self._get(url))

    def info(self, repo: str, revision: Optional[str]) -> dict:
        url = f"{_BASE}/api/datasets/{repo}"
        if revision:
            url += f"?revision={revision}"
        try:
            return self._get_json(url)
        except Exception:
            return {}

    def tree(self, repo: str, revision: Optional[str]) -> list:
        rev = revision or "main"
        try:
            return self._get_json(f"{_BASE}/api/datasets/{repo}/tree/{rev}?recursive=true")
        except Exception:
            return []

    def file_text(self, repo: str, revision: Optional[str], path: str) -> Optional[str]:
        rev = revision or "main"
        try:
            return self._get(f"{_BASE}/datasets/{repo}/resolve/{rev}/{path}")
        except Exception:
            return None

    def croissant(self, repo: str, revision: Optional[str]):
        try:
            return self._get_json(f"{_BASE}/api/datasets/{repo}/croissant")
        except Exception:
            return None

    # --- datasets-server (config choice, split totals, capped rows) ---------

    def _ranked_configs(self, repo: str):
        """[(config, [split_meta sorted by num_rows desc])] ranked by total rows
        desc (from datasets-server /size), else /splits config list."""
        try:
            size_splits = self._get_json(f"{_DS_SERVER}/size?dataset={repo}").get("size", {}).get("splits", [])
        except Exception:
            size_splits = []
        ranked = []
        if size_splits:
            per_config = {}
            for s in size_splits:
                c, sp = s.get("config"), s.get("split")
                if isinstance(c, str) and isinstance(sp, str):
                    per_config.setdefault(c, []).append(
                        {"name": sp, "num_rows": s.get("num_rows"), "num_bytes": s.get("num_bytes")})
            for c, meta in per_config.items():
                meta.sort(key=lambda sm: (sm.get("num_rows") or 0), reverse=True)
                ranked.append((c, meta, sum((sm.get("num_rows") or 0) for sm in meta)))
            ranked.sort(key=lambda t: t[2], reverse=True)
            return [(c, meta) for c, meta, _ in ranked]
        try:
            pairs = self._get_json(f"{_DS_SERVER}/splits?dataset={repo}").get("splits") or []
        except Exception:
            pairs = []
        by_cfg = {}
        for p in pairs:
            c, sp = p.get("config"), p.get("split")
            if isinstance(c, str) and isinstance(sp, str):
                by_cfg.setdefault(c, []).append({"name": sp, "num_rows": None, "num_bytes": None})
        return [(c, m) for c, m in by_cfg.items()]

    def _fetch_config_rows(self, repo: str, config: str, split_meta: list) -> dict:
        out: dict = {}
        for sm in split_meta[: self.max_splits]:
            split = sm["name"]
            collected, offset = [], 0
            while offset < self.rows_per_split:
                length = min(100, self.rows_per_split - offset)
                url = (f"{_DS_SERVER}/rows?dataset={repo}&config={config}"
                       f"&split={split}&offset={offset}&length={length}")
                try:
                    data = self._get_json(url)
                except Exception:
                    break
                batch = data.get("rows") or []
                if not batch:
                    break
                for rr in batch:
                    row = rr.get("row")
                    if isinstance(row, dict):
                        collected.append(row)
                offset += length
                if len(batch) < length:
                    break
            if collected:
                out[split] = collected
        return out

    def _ensure_resolved(self, repo: str) -> dict:
        """Pick the largest config whose rows endpoint actually serves rows, so
        content-rich multi-config datasets (wikipedia) sample real text and a
        huge-but-unserved config never shadows a smaller served one (FineFineWeb).
        Memoised per repo. ``splits`` reflects the config actually used; if no
        config serves rows, the top-ranked config's totals are kept (honest
        denominator) with an empty sample."""
        if repo in self._resolved:
            return self._resolved[repo]
        ranked = self._ranked_configs(repo)
        used_splits, rows = (ranked[0][1] if ranked else []), {}
        for config, split_meta in ranked[: self.max_configs_tried]:
            fetched = self._fetch_config_rows(repo, config, split_meta)
            if fetched:
                used_splits, rows = split_meta, fetched
                break
        self._resolved[repo] = {"splits": list(used_splits), "rows": rows}
        return self._resolved[repo]

    def splits(self, repo: str, revision: Optional[str]) -> list:
        return list(self._ensure_resolved(repo)["splits"])

    def rows(self, repo: str, revision: Optional[str]) -> dict:
        return dict(self._ensure_resolved(repo)["rows"])
