"""Scrape Anime Mirchi (animemirchi.com) for regional anime dub news, announcements, and schedules.

Extracts post titles, URLs, publication dates, and tags.
Filters out meme posts, edits, and non-release content.
Labels lineup/compilation articles so reviewers know to extract individual titles.
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

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sources.json"

DEFAULT_RSS_URL = "https://animemirchi.com/feed/"

IGNORE_KEYWORDS = [
    "meme", "funny", "edit", "amv", "cosplay", "fanart", "tier list",
    "top 10", "opinion", "review", "wallpaper", "quiz"
]

LINEUP_KEYWORDS = [
    "lineup", "lineup revealed", "slate", "schedule", "upcoming", "list", "compilation", "announced"
]

TV_CHANNELS = [
    "Sony YAY!", "Cartoon Network", "Zee Cafe", "ETV Bal Bharat",
    "Hungama", "Disney", "Nick"
]

LANGUAGES = ["Hindi", "Tamil", "Telugu", "Malayalam", "Bengali", "Marathi", "Kannada"]


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def is_release_content(title: str, content: str) -> bool:
    text = f"{title} {content}".lower()
    if any(k in text for k in IGNORE_KEYWORDS):
        return False
    keywords = ["dub", "release", "airing", "schedule", "season", "episode", "announced", "streaming", "premiere", "lineup"]
    return any(k in text for k in keywords)


def is_lineup_article(title: str, content: str) -> bool:
    text = f"{title} {content}".lower()
    return any(k in text for k in LINEUP_KEYWORDS)


def detect_metadata(text: str) -> dict:
    text_lower = text.lower()
    detected_langs = [l for l in LANGUAGES if l.lower() in text_lower]
    detected_tv = [c for c in TV_CHANNELS if c.lower() in text_lower]
    return {
        "languages": detected_langs or ["Hindi"],
        "tv_channels": detected_tv,
        "medium": "TV" if detected_tv else "OTT",
    }


def fetch_animemirchi_candidates() -> list[dict]:
    config = load_config()
    scrapers = config.get("web_scrapers") or []
    rss_url = DEFAULT_RSS_URL
    for s in scrapers:
        if s.get("name") == "Anime Mirchi" and s.get("rss_url"):
            rss_url = s["rss_url"]

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(rss_url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read()
            root = ET.fromstring(xml_data)
    except Exception as exc:
        print(f"Could not fetch Anime Mirchi RSS feed ({rss_url}): {exc}", file=sys.stderr)
        return []

    candidates = []
    items = root.findall(".//item")
    for item in items:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        description = (item.findtext("description") or "").strip()

        clean_desc = re.sub(r"<[^>]+>", "", description)
        if not is_release_content(title, clean_desc):
            continue

        meta = detect_metadata(f"{title} {clean_desc}")
        is_lineup = is_lineup_article(title, clean_desc)

        notes = (
            "⚠️ LINEUP / MULTI-ANIME ARTICLE: Do NOT accept as a single entry! Open link to extract individual anime titles."
            if is_lineup
            else f"Scraped from Anime Mirchi. Languages: {', '.join(meta['languages'])}. Medium: {meta['medium']}."
        )

        candidates.append({
            "video_id": link,
            "video_title": f"[AnimeMirchi] {title}",
            "video_url": link,
            "published_at": pub_date,
            "source": "website:animemirchi",
            "detected_languages": meta["languages"],
            "detected_channels": meta["tv_channels"],
            "medium": meta["medium"],
            "is_lineup": is_lineup,
            "status": "needs_review",
            "notes": notes,
        })

    return candidates


if __name__ == "__main__":
    c = fetch_animemirchi_candidates()
    print(f"Fetched {len(c)} candidates from Anime Mirchi.")
