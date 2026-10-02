"""aninidhi: track official regional and Hindi dubs for anime."""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
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
    "get_upcoming",
    "search",
    "get_season",
    "get_by_platform",
    "get_by_language",
    "get_by_medium",
    "get_dub_info",
    "get_series_info",
    "get_airing",
    "multi_platform_dubs",
    "platform_stats",
    "list_all",
    "refresh",
    "data_source",
]


def _normalize_dub(d: dict, default_lang: str = "Hindi") -> dict:
    dub = dict(d)
    dub.setdefault("language", default_lang)
    dub.setdefault("medium", "OTT" if "TV" not in dub.get("platform", "") else "TV")
    return dub


def _get_all_dubs(anime: dict) -> List[dict[str, Any]]:
    dubs = [
        _normalize_dub(d, "Hindi")
        for d in anime.get("hindi_dubs", [])
    ]
    for d in anime.get("dubs", []):
        normalized = _normalize_dub(d, d.get("language", "Hindi"))
        if not any(
            x.get("platform") == normalized.get("platform")
            and x.get("language") == normalized.get("language")
            and x.get("release_date") == normalized.get("release_date")
            for x in dubs
        ):
            dubs.append(normalized)
    return dubs


def _dub_dates(anime: dict) -> List[str]:
    return [str(d["release_date"]).strip() for d in _get_all_dubs(anime) if d.get("release_date")]


def _max_date_key(anime: dict) -> tuple[int, str]:
    dates = _dub_dates(anime)
    if not dates:
        return (0, "")
    iso_dates = [d for d in dates if re.match(r"^\d{4}", d)]
    if iso_dates:
        return (1, max(iso_dates))
    return (0, max(dates))


def list_all() -> List[dict[str, Any]]:
    """Every anime entry the dataset knows about, dubbed or not."""
    return load_all()


def get_latest(limit: int = 10, dubbed_only: bool = True, language: str | None = None) -> List[dict[str, Any]]:
    """Most recently dubbed anime, newest dub activity first."""
    data = load_all()
    if language:
        lang_needle = language.strip().lower()
        data = [
            a for a in data
            if any((d.get("language") or "").lower() == lang_needle for d in _get_all_dubs(a))
        ]
    elif dubbed_only:
        data = [a for a in data if (a.get("hindi_available") or a.get("dubs")) and _dub_dates(a)]
    data.sort(key=_max_date_key, reverse=True)
    return data[:limit]


def get_upcoming(language: str | None = None) -> List[dict[str, Any]]:
    """All scheduled/upcoming anime dubs (announced with future date or TBA/without date)."""
    data = load_all()
    today_str = datetime.now().strftime("%Y-%m-%d")
    results = []
    for a in data:
        all_dubs = _get_all_dubs(a)
        upcoming_dubs = [
            d for d in all_dubs
            if (
                d.get("status") in ("Upcoming", "Announced", "TBA")
                or any(k in str(d.get("release_date", "")).lower() for k in ("tba", "announced", "coming soon", "unreleased"))
                or (d.get("release_date") and str(d.get("release_date")) > today_str)
            )
        ]
        if language:
            upcoming_dubs = [d for d in upcoming_dubs if (d.get("language") or "").lower() == language.strip().lower()]
        if upcoming_dubs:
            results.append(a)
    return results


def search(title: str) -> List[dict[str, Any]]:
    """Case-insensitive substring search over anime titles."""
    needle = title.strip().lower()
    return [a for a in load_all() if needle in (a.get("title") or "").lower()]


def get_airing() -> List[dict[str, Any]]:
    """All anime currently marked as Airing on at least one platform/channel."""
    return [
        a
        for a in load_all()
        if a.get("status") == "Airing"
        or any(d.get("status") == "Airing" for d in _get_all_dubs(a))
    ]


def get_series_info(title: str) -> dict[str, Any]:
    """Get aggregated series information including all seasons, platforms, and airing status."""
    matches = search(title)
    if not matches:
        return {"query": title, "total_entries": 0, "seasons": [], "overall_status": "Unknown"}

    series_title = re.sub(r"\s*\([^)]*\)", "", matches[0]["title"])
    series_title = re.sub(r":.*", "", series_title).strip()

    seasons = []
    has_airing = False
    airing_seasons = []

    for a in matches:
        all_dubs = _get_all_dubs(a)
        is_airing = a.get("status") == "Airing" or any(
            d.get("status") == "Airing" for d in all_dubs
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
                    d["platform"] for d in all_dubs if d.get("platform")
                )
            ),
            "dubs": all_dubs,
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
    """All dubbed anime with a release on a given platform/channel."""
    needle = platform.strip().lower()
    return [
        a
        for a in load_all()
        if any(needle in (d.get("platform") or "").lower() for d in _get_all_dubs(a))
    ]


def get_by_language(language: str) -> List[dict[str, Any]]:
    """All anime with official dubs in `language` (e.g. Hindi, Tamil, Telugu)."""
    needle = language.strip().lower()
    return [
        a
        for a in load_all()
        if any(needle == (d.get("language") or "").lower() for d in _get_all_dubs(a))
    ]


def get_by_medium(medium: str) -> List[dict[str, Any]]:
    """All anime available on a given medium (e.g. TV, OTT, YouTube)."""
    needle = medium.strip().lower()
    return [
        a
        for a in load_all()
        if any(needle == (d.get("medium") or "").lower() for d in _get_all_dubs(a))
    ]


def get_dub_info(title: str) -> List[dict[str, Any]]:
    """Full per-platform dub breakdown for anime matching `title`."""
    return search(title)


def multi_platform_dubs(min_platforms: int = 2) -> List[dict[str, Any]]:
    """Anime dubbed independently on `min_platforms` or more platforms."""
    result = []
    for a in load_all():
        platforms = {d.get("platform") for d in _get_all_dubs(a)}
        if len(platforms) >= min_platforms:
            result.append(a)
    return result


def platform_stats() -> dict[str, int]:
    """Count of dubbed releases per platform/channel."""
    counter: Counter[str] = Counter()
    for a in load_all():
        for d in _get_all_dubs(a):
            if d.get("platform"):
                counter[d["platform"]] += 1
    return dict(counter)
