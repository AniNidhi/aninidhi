"""aninidhi: track which anime have official Hindi dubs."""
from __future__ import annotations

from collections import Counter
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version
from typing import Any, List

from .data import data_source, load_all, refresh

try:
    __version__ = _version("aninidhi")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "get_latest",
    "search",
    "get_season",
    "get_by_platform",
    "get_dub_info",
    "get_series_info",
    "get_airing",
    "multi_platform_dubs",
    "platform_stats",
    "list_all",
    "refresh",
    "data_source",
]


def _dub_dates(anime: dict) -> List[str]:
    return [d["release_date"] for d in anime.get("hindi_dubs", []) if d.get("release_date")]


def list_all() -> List[dict[str, Any]]:
    """Every anime entry the dataset knows about, dubbed or not."""
    return load_all()


def get_latest(limit: int = 10, dubbed_only: bool = True) -> List[dict[str, Any]]:
    """Most recently Hindi-dubbed anime, newest dub activity first."""
    data = load_all()
    if dubbed_only:
        data = [a for a in data if a.get("hindi_available") and _dub_dates(a)]
    data.sort(key=lambda a: max(_dub_dates(a), default=""), reverse=True)
    return data[:limit]


def search(title: str) -> List[dict[str, Any]]:
    """Case-insensitive substring search over anime titles."""
    needle = title.strip().lower()
    return [a for a in load_all() if needle in (a.get("title") or "").lower()]


def get_airing() -> List[dict[str, Any]]:
    """All anime currently marked as Airing on at least one platform."""
    return [
        a
        for a in load_all()
        if a.get("status") == "Airing"
        or any(d.get("status") == "Airing" for d in a.get("hindi_dubs", []))
    ]


def get_series_info(title: str) -> dict[str, Any]:
    """Get aggregated series information including all seasons, platforms, and airing status."""
    matches = search(title)
    if not matches:
        return {"query": title, "total_entries": 0, "seasons": [], "overall_status": "Unknown"}

    import re
    series_title = re.sub(r"\s*\([^)]*\)", "", matches[0]["title"])
    series_title = re.sub(r":.*", "", series_title).strip()

    seasons = []
    has_airing = False
    airing_seasons = []

    for a in matches:
        is_airing = a.get("status") == "Airing" or any(
            d.get("status") == "Airing" for d in a.get("hindi_dubs", [])
        )
        if is_airing:
            has_airing = True
            airing_seasons.append(a["title"])
        seasons.append({
            "id": a.get("id"),
            "title": a.get("title"),
            "season": a.get("season"),
            "status": "Airing" if is_airing else "Finished",
            "platforms": list(
                dict.fromkeys(
                    d["platform"] for d in a.get("hindi_dubs", []) if d.get("platform")
                )
            ),
            "hindi_dubs": a.get("hindi_dubs", []),
        })

    return {
        "query": title,
        "series_title": series_title,
        "total_entries": len(matches),
        "overall_status": "Airing" if has_airing else "Finished",
        "airing_seasons": airing_seasons,
        "seasons": seasons,
    }


def get_season(year: int, season: str) -> List[dict[str, Any]]:
    """All anime from a given MyAnimeList season, e.g. get_season(2024, 'winter')."""
    season = season.strip().lower()
    return [
        a
        for a in load_all()
        if a.get("season_year") == year and (a.get("season") or "").lower() == season
    ]


def get_by_platform(platform: str) -> List[dict[str, Any]]:
    """All Hindi-dubbed anime with a release on a given platform."""
    needle = platform.strip().lower()
    return [
        a
        for a in load_all()
        if a.get("hindi_available")
        and any(needle in (d.get("platform") or "").lower() for d in a.get("hindi_dubs", []))
    ]


def get_dub_info(title: str) -> List[dict[str, Any]]:
    """Full per-platform dub breakdown for anime matching `title`."""
    return search(title)


def multi_platform_dubs(min_platforms: int = 2) -> List[dict[str, Any]]:
    """Anime dubbed independently on `min_platforms` or more platforms."""
    result = []
    for a in load_all():
        platforms = {d.get("platform") for d in a.get("hindi_dubs", [])}
        if len(platforms) >= min_platforms:
            result.append(a)
    return result


def platform_stats() -> dict[str, int]:
    """Count of Hindi-dubbed releases per platform."""
    counter: Counter[str] = Counter()
    for a in load_all():
        for d in a.get("hindi_dubs", []):
            if d.get("platform"):
                counter[d["platform"]] += 1
    return dict(counter)

