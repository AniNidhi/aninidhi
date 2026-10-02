"""Poll Instagram handles for regional anime dub announcements, trailers, and streaming schedules.

Features:
- Configurable accounts via config/sources.json, INSTAGRAM_ACCOUNTS env var, CLI arguments, and default accounts.
- Reads video/post captions for phrases like "streaming today in hindi", "hindi dub streaming weekly", "now streaming".
- Filters memes, fan edits, and non-release posts automatically.
- Detects languages, broadcast medium (TV/OTT), schedule dates, and Airing vs Upcoming status.
- Supports session cookies from config/instagram_cookies.txt, INSTAGRAM_COOKIES_FILE env var, or local instaloader sessions.

Usage:
    python scripts/fetch_instagram.py [--accounts user1 user2] [--cookies path/to/cookies.txt]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sources.json"

DEFAULT_IGNORE_KEYWORDS = [
    "meme", "funny", "edit", "amv", "cosplay", "fanart", "shitpost", "trend", "viral",
    "quiz", "wallpaper", "top 10", "opinion", "reaction"
]

DEFAULT_TARGET_ACCOUNTS = [
    "crunchyrollin",
    "museindia",
    "sony_yay",
    "cartoonnetworkindia",
    "zeecafeindia",
    "etvbalbharat",
    "anime_mirchi",
    "netflix_in",
    "primevideoin",
    "disneyplus_hotstar",
    "animetimesindia",
]

LANGUAGES = ["Hindi", "Tamil", "Telugu", "Malayalam", "Bengali", "Marathi", "Kannada"]

STREAMING_INTENT_PATTERNS = [
    r"streaming\s+today\s+in\s+([a-zA-Z]+)",
    r"([a-zA-Z]+)\s+dub\s+streaming\s+weekly",
    r"now\s+streaming\s+(?:in\s+([a-zA-Z]+))?",
    r"streaming\s+now\s+(?:in\s+([a-zA-Z]+))?",
    r"episodes?\s+dropping\s+(?:every|weekly)",
    r"new\s+episodes?\s+(?:every|weekly|out\s+now)",
    r"watch\s+(?:now\s+)?in\s+([a-zA-Z]+)",
    r"now\s+available\s+in\s+([a-zA-Z]+)",
    r"dubbed\s+in\s+([a-zA-Z]+)",
    r"premieres?\s+(?:today|tomorrow|this\s+week|on\s+[\w\s\d]+)",
    r"airing\s+(?:now|every|weekly|on\s+[\w\s]+)",
    r"hindi\s+dub",
    r"season\s+\d+\s+(?:is\s+here|streaming)",
]


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def load_target_accounts(cli_accounts: list[str] | None = None) -> list[str]:
    """Load target accounts from CLI args, INSTAGRAM_ACCOUNTS env var, config file, and defaults."""
    accounts = list(DEFAULT_TARGET_ACCOUNTS)

    # Config file accounts
    config = load_config()
    cfg_accounts = (config.get("instagram") or {}).get("target_accounts") or []
    for acc in cfg_accounts:
        clean = acc.strip().lower().lstrip("@")
        if clean and clean not in accounts:
            accounts.append(clean)

    # Environment variable (comma or space separated)
    env_accounts = os.environ.get("INSTAGRAM_ACCOUNTS", "")
    if env_accounts:
        for acc in re.split(r"[,;\s]+", env_accounts):
            clean = acc.strip().lower().lstrip("@")
            if clean and clean not in accounts:
                accounts.append(clean)

    # CLI accounts override / prepend
    if cli_accounts:
        for acc in cli_accounts:
            clean = acc.strip().lower().lstrip("@")
            if clean and clean not in accounts:
                accounts.insert(0, clean)

    return accounts


def is_meme_or_non_release(caption: str, ignore_keywords: list[str]) -> bool:
    t = caption.lower()
    if any(re.search(rf"\b{re.escape(k)}\b", t) for k in ignore_keywords):
        return True

    # Check for release / streaming intent
    for pattern in STREAMING_INTENT_PATTERNS:
        if re.search(pattern, t, flags=re.I):
            return False

    keywords = [
        "dub", "release", "trailer", "schedule", "anime", "voice artist", "voice actor",
        "airing", "episodes", "streaming", "premiere", "coming soon", "hindi", "tamil", "telugu"
    ]
    return not any(k in t for k in keywords)


def detect_metadata_from_caption(caption: str) -> dict:
    caption_lower = caption.lower()
    detected_langs = [l for l in LANGUAGES if l.lower() in caption_lower]

    # Detect medium
    is_tv = any(c in caption_lower for c in ["sony yay", "cartoon network", "zee cafe", "etv", "television", "tv"])
    medium = "TV" if is_tv else "OTT"

    # Detect status
    today = datetime.now().date()
    status = "Finished"
    if any(p in caption_lower for p in ["streaming today", "now streaming", "streaming now", "weekly", "dropping weekly", "airing now", "episodes out now", "ep 1 out"]):
        status = "Airing"
    elif any(p in caption_lower for p in ["coming soon", "announced", "premieres on", "schedule", "releasing soon", "upcoming"]):
        status = "Upcoming"

    return {
        "languages": detected_langs or ["Hindi"],
        "medium": medium,
        "status": status,
    }


def clean_caption_title(caption: str, username: str) -> str:
    """Extract a clean title headline from an Instagram post caption."""
    # Split into lines and take the first informative line
    lines = [line.strip() for line in caption.splitlines() if line.strip()]
    first_line = ""
    for line in lines:
        # Remove hashtags and mentions
        cleaned = re.sub(r"#[A-Za-z0-9_]+", "", line)
        cleaned = re.sub(r"@[A-Za-z0-9_.]+", "", cleaned)
        cleaned = re.sub(r"[🔥✨🎉📢🚨👉👇‼️]+", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) >= 4:
            first_line = cleaned[:100]
            break

    return first_line or f"Release announcement by @{username}"


def fetch_via_instaloader(accounts: list[str], cookie_file: str | None, ignore_keywords: list[str]) -> list[dict]:
    try:
        import instaloader
    except ImportError:
        print("instaloader package not installed - skipping instaloader extraction.", file=sys.stderr)
        return []

    L = instaloader.Instaloader(download_pictures=False, download_videos=False, download_comments=False)
    
    # Check cookie file paths
    cookie_paths = [
        cookie_file,
        str(ROOT / "config" / "instagram_cookies.txt"),
        os.environ.get("INSTAGRAM_COOKIES_FILE"),
    ]
    loaded_session = False
    for cp in cookie_paths:
        if cp and Path(cp).exists():
            try:
                L.load_session_from_file(cp)
                loaded_session = True
                print(f"Loaded Instagram session from {cp}")
                break
            except Exception as err:
                print(f"Warning: Could not load Instagram session from {cp}: {err}", file=sys.stderr)

    candidates = []
    for username in accounts:
        try:
            profile = instaloader.Profile.from_username(L.context, username)
            count = 0
            for post in profile.get_posts():
                if count >= 6:  # check 6 most recent posts
                    break
                count += 1

                caption = post.caption or ""
                if is_meme_or_non_release(caption, ignore_keywords):
                    continue

                meta = detect_metadata_from_caption(caption)
                post_url = f"https://www.instagram.com/p/{post.shortcode}/"
                title_summary = clean_caption_title(caption, username)

                candidates.append({
                    "video_id": post_url,
                    "video_title": f"[Instagram @{username}] {title_summary}",
                    "video_url": post_url,
                    "published_at": post.date_utc.isoformat() if post.date_utc else "",
                    "source": f"instagram:{username}",
                    "detected_languages": meta["languages"],
                    "medium": meta["medium"],
                    "detected_status": meta["status"],
                    "caption_full": caption[:300],
                    "status": "needs_review",
                    "notes": f"Instagram post from @{username} ({meta['status']}). Caption: {title_summary}",
                })
        except Exception as exc:
            print(f"Could not fetch Instagram posts for @{username}: {exc}", file=sys.stderr)

    return candidates


def fetch_instagram_candidates(cli_accounts: list[str] | None = None, cookie_file: str | None = None) -> list[dict]:
    config = load_config()
    insta_config = config.get("instagram") or {}

    accounts = load_target_accounts(cli_accounts)
    ignore_keywords = insta_config.get("ignore_keywords") or DEFAULT_IGNORE_KEYWORDS
    cookie_path = cookie_file or insta_config.get("cookies_file") or os.environ.get("INSTAGRAM_COOKIES_FILE")

    candidates = fetch_via_instaloader(accounts, cookie_path, ignore_keywords)
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Instagram anime dub announcements and streaming captions.")
    parser.add_argument("--accounts", nargs="+", default=None, help="Additional Instagram usernames to check.")
    parser.add_argument("--cookies", default=None, help="Path to Instagram cookies/session file.")
    args = parser.parse_args()

    candidates = fetch_instagram_candidates(cli_accounts=args.accounts, cookie_file=args.cookies)
    print(f"Fetched {len(candidates)} Instagram candidates across {len(load_target_accounts(args.accounts))} accounts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
