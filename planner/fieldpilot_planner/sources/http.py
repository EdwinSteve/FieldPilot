"""HTTP GET with retries and an on-disk cache keyed by the request's SHA-256.

A cached response is never fetched again, so an interrupted download resumes
where it stopped, and the manifest can list exactly what was used.
"""

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

USER_AGENT = "FieldPilot-planner/0.1 (research; contact via repository)"
RETRYABLE = {429, 500, 502, 503, 504}

Query = Mapping[str, str | int | float | Sequence[str]]


def build_url(base: str, query: Query) -> str:
    return f"{base}?{urllib.parse.urlencode(query, doseq=True)}"


class CachedHttp:
    def __init__(self, cache_dir: Path, retries: int = 6, timeout_s: float = 120.0) -> None:
        self._cache = cache_dir
        self._retries = retries
        self._timeout = timeout_s
        self._cache.mkdir(parents=True, exist_ok=True)

    def path_for(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode()).hexdigest()
        return self._cache / f"{digest}.body"

    def is_cached(self, url: str) -> bool:
        return self.path_for(url).exists()

    def get_text(self, url: str) -> str:
        path = self.path_for(url)
        if path.exists():
            return path.read_text(encoding="utf-8")
        body = self._fetch(url)
        tmp = path.with_suffix(".part")
        tmp.write_text(body, encoding="utf-8")
        tmp.replace(path)  # atomic: a crash never leaves a half-written cache entry
        return body

    def get_json(self, url: str) -> Any:
        return json.loads(self.get_text(url))

    def _fetch(self, url: str) -> str:
        delay = 5.0
        for attempt in range(1, self._retries + 1):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=self._timeout) as response:
                    return str(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                if error.code not in RETRYABLE or attempt == self._retries:
                    raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if attempt == self._retries:
                    raise
            time.sleep(delay)
            delay = min(delay * 2, 120.0)
        raise RuntimeError("unreachable")
