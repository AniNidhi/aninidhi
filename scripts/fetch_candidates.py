"""Poll multiple free sources for new regional & Hindi dub anime candidates.

Sources:
- YouTube (Muse Hindi Dub, Muse India main channel, Sony YAY!, Cartoon Network India, etc.)
- Crunchyroll News RSS & Google Alerts RSS feeds
- Anime Mirchi web scraper (animemirchi.com)
- Instagram news & release poller (with session cookies & auto meme filtering)

Usage:
    python scripts/fetch_candidates.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# Add scripts directory to path to import fetcher modules
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_animemirchi import fetch_animemirchi_candidates
from fetch_instagram import fetch_instagram_candidates

ANIME_PATH = ROOT / "src" / "aninidhi" / "data" / "anime.json"
PENDING_PATH = ROOT / "pending_review.json"

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
CRUNCHYROLL_NEWS_RSS = "https://cr-news-api-service.prd.crunchyrollsvc.com/v1/en-US/rss"

YOUTUBE_CHANNELS = [
    ("Muse_HindiDub", False),
    ("MuseIndiaChannel", True),
]


def youtube_api_get(endpoint: str, params: dict) -> dict:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("YOUTUBE_API_KEY not set - skipping YouTube sources.", file=sys.stderr)
        return {}
    url = f"{YOUTUBE_API_BASE}/{endpoint}?{urllib.parse.urlencode({**params, 'key': api_key})}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read())


def get_uploads_playlist_id(handle: str) -> str | None:
    data = youtube_api_get("channels", {"part": "contentDetails", "forHandle": f"@{handle}"})
    items = data.get("items") or []
    if not items:
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def get_recent_uploads(playlist_id: str, max_results: int = 25) -> list[dict]:
    data = youtube_api_get(
        "playlistItems",
        {"part": "snippet", "playlistId": playlist_id, "maxResults": max_results},
    )
    return data.get("items") or []


def fetch_youtube_candidates() -> list[dict]:
    candidates = []
    for handle, needs_filter in YOUTUBE_CHANNELS:
        playlist_id = get_uploads_playlist_id(handle)
        if not playlist_id:
            continue
        for item in get_recent_uploads(playlist_id):
            snippet = item["snippet"]
            title = snippet["title"]
            if needs_filter and "hindi" not in title.lower():
                continue
            video_id = snippet["resourceId"]["videoId"]
            candidates.append({
                "video_id": video_id,
                "video_title": title,
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
                "published_at": snippet["publishedAt"],
                "source": f"youtube:{handle}",
                "detected_languages": ["Hindi"],
                "medium": "YouTube",
            })
    return candidates


def fetch_rss_candidates(url: str, source_label: str, require_hindi_keyword: bool) -> list[dict]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            root = ET.fromstring(resp.read())
    except Exception as exc:
        print(f"Could not fetch RSS from {source_label}: {exc}", file=sys.stderr)
        return []

    candidates = []
    items = root.findall(".//item")
    if items:
        for item in items:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            description = (item.findtext("description") or "").strip()
            if require_hindi_keyword and "hindi" not in f"{title} {description}".lower():
                continue
            candidates.append({
                "video_id": link,
                "video_title": title,
                "video_url": link,
                "published_at": pub_date,
                "source": source_label,
                "detected_languages": ["Hindi"],
                "medium": "OTT",
            })
    return candidates


def load(path: Path) -> list:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def load_known_titles() -> list[str]:
    return [a["title"].lower() for a in load(ANIME_PATH)]


def strip_tags(video_title: str) -> str:
    t = re.sub(r"\[[^\]]*\]", "", video_title)
    t = re.sub(r"\b(ep|episode)\.?\s*\d+\b", "", t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip().lower()


def looks_like_reupload(video_title: str, known_titles: list[str]) -> bool:
    guess = strip_tags(video_title)
    return any(guess in known or known in guess for known in known_titles if known)


def main() -> int:
    pending = load(PENDING_PATH)
    known_ids = {entry["video_id"] for entry in pending}
    known_titles = load_known_titles()

    raw_candidates = fetch_youtube_candidates()
    raw_candidates += fetch_rss_candidates(
        CRUNCHYROLL_NEWS_RSS, "rss:crunchyroll-news", require_hindi_keyword=True
    )
    alerts_urls = [u.strip() for u in os.environ.get("GOOGLE_ALERTS_RSS_URLS", "").split(",") if u.strip()]
    for i, alerts_url in enumerate(alerts_urls, 1):
        raw_candidates += fetch_rss_candidates(
            alerts_url, f"rss:google-alerts-{i}", require_hindi_keyword=False
        )

    # Scrape Anime Mirchi & Instagram
    raw_candidates += fetch_animemirchi_candidates()
    raw_candidates += fetch_instagram_candidates()

    new_count, reupload_count = 0, 0
    for c in raw_candidates:
        if not c["video_id"] or c["video_id"] in known_ids:
            continue
        known_ids.add(c["video_id"])
        is_reupload = looks_like_reupload(c["video_title"], known_titles)
        pending.append({
            **c,
            "status": "needs_review",
            "notes": c.get("notes") or (
                "Likely re-upload of an existing dub - verify before treating as new."
                if is_reupload
                else "Confirm it's a real dub (not a trailer/rumor), then match or add an anime.json entry."
            ),
        })
        new_count += 1
        reupload_count += is_reupload

    PENDING_PATH.write_text(json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Found {new_count} new candidate(s) across YouTube, RSS, Anime Mirchi, and Instagram. "
        f"{reupload_count} flagged as likely re-uploads. Total pending: {len(pending)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
