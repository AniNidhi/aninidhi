from __future__ import annotations

import json
import os
import time
import urllib.request
from importlib import resources
from pathlib import Path
from typing import Any, List

DEFAULT_SOURCE_URL = os.environ.get(
    "ANINIDHI_SOURCE_URL",
    "https://raw.githubusercontent.com/AniNidhi/aninidhi/main/src/aninidhi/data/anime.json",
)

CACHE_DIR = Path(os.environ.get("ANINIDHI_CACHE_DIR", str(Path.home() / ".cache" / "aninidhi")))
CACHE_FILE = CACHE_DIR / "anime.json"
CACHE_MAX_AGE_SECONDS = 24 * 60 * 60


def _bundled_data_path():
    return resources.files("aninidhi").joinpath("data/anime.json")


def _load_json(path) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _cache_is_fresh() -> bool:
    if not CACHE_FILE.exists():
        return False
    age = time.time() - CACHE_FILE.stat().st_mtime
    return age < CACHE_MAX_AGE_SECONDS


def refresh(url: str | None = None, force: bool = False) -> int:
    """Fetch the dataset from `url` (or ANINIDHI_SOURCE_URL) and cache it."""
    source = url or DEFAULT_SOURCE_URL
    if not source:
        raise RuntimeError(
            "No source URL configured. Pass one explicitly (refresh(url=...)) "
            "or set the ANINIDHI_SOURCE_URL environment variable."
        )

    if not force and _cache_is_fresh():
        return len(_load_json(CACHE_FILE))

    with urllib.request.urlopen(source, timeout=10) as response:
        payload = response.read()

    data = json.loads(payload)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return len(data)


def load_all(auto_refresh: bool = True) -> List[dict]:
    """Return every known anime entry."""
    if auto_refresh and DEFAULT_SOURCE_URL and not _cache_is_fresh():
        try:
            refresh()
        except Exception:
            pass

    if CACHE_FILE.exists():
        return _load_json(CACHE_FILE)
    return _load_json(_bundled_data_path())


def data_source() -> str:
    """Report which data source the next query would use."""
    if DEFAULT_SOURCE_URL and _cache_is_fresh():
        return f"cache (fresh, from {DEFAULT_SOURCE_URL})"
    if DEFAULT_SOURCE_URL:
        return f"cache or remote refresh ({DEFAULT_SOURCE_URL})"
    if CACHE_FILE.exists():
        return "local cache (no remote source configured)"
    return "bundled snapshot (offline mode)"