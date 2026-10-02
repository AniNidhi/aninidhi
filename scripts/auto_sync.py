"""Self-automated synchronization pipeline for AniNidhi.

1. Scrapes all sources (YouTube, Anime Mirchi, Instagram, Crunchyroll RSS, Google Alerts RSS).
2. Scores candidate confidence:
   - High confidence (>= 80): Auto-adds directly into anime.json and auto-enriches metadata via AniList.
   - Low confidence (< 80), lineup articles, or ambiguous multi-platform conflicts: Routed to pending_review.json.
3. Supports both scheduled releases with exact dates (YYYY-MM-DD) and TBA / unannounced dates.
4. Auto-sorts and renumbers the dataset.

Usage:
    python scripts/auto_sync.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from enrich_anilist import base_title, clean_synopsis, query_anilist
from fetch_animemirchi import fetch_animemirchi_candidates
from fetch_candidates import (
    CRUNCHYROLL_NEWS_RSS,
    fetch_rss_candidates,
    fetch_youtube_candidates,
    load,
)
from fetch_instagram import fetch_instagram_candidates

ANIME_PATH = ROOT / "src" / "aninidhi" / "data" / "anime.json"
PENDING_PATH = ROOT / "pending_review.json"


def normalize_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"\[[^\]]*\]", "", t)
    t = re.sub(r"\b(hindi dub|dubbed in hindi|hindi dubbing|official hindi dub)\b", "", t, flags=re.I)
    t = re.sub(r"\b(ep|episode|episodes)\.?\s*\d+(\s*-\s*\d+)?\b", "", t, flags=re.I)
    t = re.sub(r"\b(season|cour|part)\s*\d+\b", "", t, flags=re.I)
    t = re.sub(r"\b(trailer|teaser|announcement|promo|review|news)\b", "", t, flags=re.I)
    t = re.sub(r"\s*\(.*?\)\s*", " ", t)
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def find_existing_match(anime_data: list[dict], title: str) -> dict | None:
    norm = normalize_title(title)
    if not norm:
        return None
    for entry in anime_data:
        entry_norm = normalize_title(entry.get("title", ""))
        if not entry_norm:
            continue
        if norm == entry_norm:
            return entry
        if len(norm) > 4 and len(entry_norm) > 4:
            if norm in entry_norm or entry_norm in norm:
                return entry
    return None


def extract_release_date(text: str, published_at: str | None = None) -> tuple[str, str]:
    """Extract release date and status (Finished, Airing, Upcoming).

    Returns: (date_str, status)
    """
    text_lower = text.lower()
    today = datetime.now().date()
    found_date = None

    # Search for ISO date YYYY-MM-DD
    iso_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if iso_match:
        try:
            found_date = datetime.strptime(iso_match.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass

    # Search for dates like "15th October 2026" or "October 15, 2026"
    if not found_date:
        month_regex = (
            r"\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
            r"(?:,?\s+20\d{2})?|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?"
            r"(?:,?\s+20\d{2})?)\b"
        )
        month_match = re.search(month_regex, text, flags=re.I)
        if month_match:
            raw = month_match.group(1)
            raw_clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", raw)
            for fmt in ("%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y", "%B %d, %Y", "%b %d, %Y"):
                try:
                    found_date = datetime.strptime(raw_clean, fmt).date()
                    break
                except ValueError:
                    continue

    if not found_date and published_at:
        try:
            pub_str = published_at.split("T")[0]
            found_date = datetime.strptime(pub_str, "%Y-%m-%d").date()
        except Exception:
            pass

    if found_date:
        date_str = found_date.strftime("%Y-%m-%d")
        if found_date > today:
            return date_str, "Upcoming"
        # If release is within last 60 days and involves episodes/series/weekly drops, mark Airing
        is_recent = (today - found_date).days <= 60
        is_episode_or_series = any(k in text_lower for k in ["episode", "ep ", "ep.", "season", "airing", "weekly", "streaming now", "premiered"])
        if is_recent and (is_episode_or_series or (today - found_date).days <= 7):
            return date_str, "Airing"
        return date_str, "Finished"

    # Dateless announcement / TBA
    return "TBA", "Upcoming"


def calculate_confidence(candidate: dict) -> tuple[int, str]:
    """Calculate confidence score (0-100) and reason."""
    source = candidate.get("source", "")
    title = candidate.get("video_title", "")
    title_lower = title.lower()

    if candidate.get("is_lineup") or "lineup" in title_lower or "compilation" in title_lower:
        return 30, "Lineup / multi-anime post requires manual splitting"

    # Meme / edit keywords
    if any(k in title_lower for k in ["meme", "edit", "amv", "quiz", "opinion", "cosplay"]):
        return 10, "Meme or fan content"

    # Direct official YouTube channel upload
    if "youtube:Muse_HindiDub" in source or "youtube:MuseIndiaChannel" in source:
        if "ep" in title_lower or "episode" in title_lower or "hindi" in title_lower:
            return 95, "Official Muse YouTube release"
        return 85, "Muse YouTube announcement"

    # Crunchyroll news
    if "rss:crunchyroll-news" in source:
        if "hindi dub" in title_lower or "hindi" in title_lower:
            return 90, "Official Crunchyroll news announcement"
        return 75, "Crunchyroll news item"

    # Instagram official channels
    if "instagram:" in source:
        official_handles = ["crunchyrollin", "museindia", "sony_yay", "cartoonnetworkindia", "zeecafeindia"]
        handle = source.split(":")[-1]
        if handle in official_handles:
            if any(k in title_lower for k in ["dub", "premiere", "airing", "release", "coming soon"]):
                return 85, f"Official Instagram post from @{handle}"
            return 70, f"General Instagram post from @{handle}"
        return 60, "Third-party Instagram post"

    # Anime Mirchi scraper
    if "animemirchi" in source:
        if any(k in title_lower for k in ["confirmed", "announced", "premiere", "release date", "dub"]):
            return 82, "Anime Mirchi release announcement"
        return 65, "Anime Mirchi general article"

    return 50, "Unverified source"


def clean_anime_title(raw_title: str) -> str:
    t = raw_title
    t = re.sub(r"^\[(AnimeMirchi|Instagram @[^\]]+|YouTube)\]\s*", "", t)
    t = re.sub(r"\[[^\]]*\]", "", t)
    t = re.sub(r"\b(Official Hindi Dub|Hindi Dub Announcement|Hindi Dubbed|Hindi Dub)\b", "", t, flags=re.I)
    t = re.sub(r"\b(Ep|Episode)\.?\s*\d+(\s*-\s*\d+)?\b", "", t, flags=re.I)
    t = re.sub(r"\b(Full Season|Part \d+|Cour \d+)\b", "", t, flags=re.I)
    t = re.sub(r"\b(Release Date Announced|Airing Date|Coming Soon|Trailer|Teaser|Promo|Announced|Announcement)\b", "", t, flags=re.I)
    t = re.sub(r"[:\-|–]\s*$", "", t)
    return re.sub(r"\s+", " ", t).strip()


def create_new_anime_entry(next_id: int, clean_title: str, dub_entry: dict) -> dict:
    # Attempt to enrich via AniList API
    search_query = base_title(clean_title)
    media = None
    try:
        media = query_anilist(search_query)
    except Exception:
        pass

    title = clean_title
    original_title = None
    genres = []
    episodes = None
    studio = None
    synopsis = None
    poster_url = None
    anilist_id = None
    anilist_url = None

    if media:
        anilist_id = media.get("id")
        anilist_url = f"https://anilist.co/anime/{anilist_id}" if anilist_id else None
        genres = media.get("genres") or []
        episodes = media.get("episodes")
        synopsis = clean_synopsis(media.get("description"))
        poster_url = (media.get("coverImage") or {}).get("large")
        studios = (media.get("studios") or {}).get("nodes") or []
        if studios:
            studio = studios[0].get("name")

    is_hindi = dub_entry.get("language", "Hindi").lower() == "hindi"
    hindi_dubs = [{
        "platform": dub_entry["platform"],
        "release_date": dub_entry["release_date"],
        "status": dub_entry["status"],
        "media_type": dub_entry.get("media_type", "series"),
    }] if is_hindi else []

    return {
        "id": next_id,
        "title": title,
        "original_title": original_title,
        "genres": genres,
        "season": None,
        "season_year": None,
        "episodes": episodes,
        "studio": studio,
        "synopsis": synopsis,
        "poster_url": poster_url,
        "mal_id": None,
        "mal_url": None,
        "anilist_id": anilist_id,
        "anilist_url": anilist_url,
        "imdb_id": None,
        "imdb_url": None,
        "imdb_rating": None,
        "hindi_available": is_hindi,
        "hindi_dubs": hindi_dubs,
        "dubs": [dub_entry],
        "notes": f"Auto-added from {dub_entry.get('platform', 'unknown')}",
    }


def auto_sync(dry_run: bool = False) -> tuple[int, int, int]:
    """Execute complete auto sync.

    Returns: (auto_added_count, auto_updated_count, sent_to_review_count)
    """
    anime_data = load(ANIME_PATH)
    pending_list = load(PENDING_PATH)
    known_pending_ids = {p["video_id"] for p in pending_list if p.get("video_id")}

    print("Fetching candidates from YouTube, Crunchyroll, Alerts, Anime Mirchi, Instagram...")
    raw_candidates = []
    raw_candidates += fetch_youtube_candidates()
    raw_candidates += fetch_rss_candidates(CRUNCHYROLL_NEWS_RSS, "rss:crunchyroll-news", require_hindi_keyword=True)
    alerts_urls = [u.strip() for u in os.environ.get("GOOGLE_ALERTS_RSS_URLS", "").split(",") if u.strip()]
    for i, alerts_url in enumerate(alerts_urls, 1):
        raw_candidates += fetch_rss_candidates(alerts_url, f"rss:google-alerts-{i}", require_hindi_keyword=False)
    raw_candidates += fetch_animemirchi_candidates()
    raw_candidates += fetch_instagram_candidates()

    next_id = max((a["id"] for a in anime_data), default=0) + 1
    auto_added = 0
    auto_updated = 0
    sent_to_review = 0

    for candidate in raw_candidates:
        c_id = candidate.get("video_id")
        if not c_id or c_id in known_pending_ids:
            continue

        confidence, reason = calculate_confidence(candidate)
        video_title = candidate.get("video_title", "")
        clean_title = clean_anime_title(video_title)
        release_date, status = extract_release_date(video_title, candidate.get("published_at"))

        platform = "Crunchyroll" if "crunchyroll" in candidate.get("source", "").lower() else (
            "Muse India" if "muse" in candidate.get("source", "").lower() else (
                "Sony YAY!" if "sony_yay" in candidate.get("source", "").lower() else (
                    "Cartoon Network" if "cartoonnetwork" in candidate.get("source", "").lower() else (
                        "Zee Cafe" if "zeecafe" in candidate.get("source", "").lower() else "OTT"
                    )
                )
            )
        )

        language = (candidate.get("detected_languages") or ["Hindi"])[0]
        medium = candidate.get("medium", "OTT")

        dub_entry = {
            "language": language,
            "platform": platform,
            "medium": medium,
            "release_date": release_date,
            "status": status,
            "media_type": "series",
        }

        # High confidence -> Auto-add / Auto-update
        if confidence >= 80 and len(clean_title) >= 3:
            existing = find_existing_match(anime_data, clean_title)
            if existing:
                # Check if dub already exists
                dubs = existing.setdefault("dubs", [])
                already_exists = any(
                    d.get("platform") == platform
                    and d.get("language") == language
                    and (d.get("release_date") == release_date or d.get("release_date") == "TBA")
                    for d in dubs
                )
                if not already_exists:
                    dubs.append(dub_entry)
                    if language.lower() == "hindi":
                        existing.setdefault("hindi_dubs", []).append({
                            "platform": platform,
                            "release_date": release_date,
                            "status": status,
                            "media_type": "series",
                        })
                        existing["hindi_available"] = True
                    auto_updated += 1
                    print(f"  [AUTO-UPDATE] Added {language} dub ({platform}, {release_date}) to '{existing['title']}'")
            else:
                # Brand new anime
                new_entry = create_new_anime_entry(next_id, clean_title, dub_entry)
                next_id += 1
                anime_data.append(new_entry)
                auto_added += 1
                print(f"  [AUTO-ADD] Created new anime entry #{new_entry['id']}: '{new_entry['title']}' [{platform}, {language}]")
            known_pending_ids.add(c_id)
        else:
            # Low confidence / ambiguous / lineup -> Route to pending review
            pending_list.append({
                **candidate,
                "status": "needs_review",
                "confidence_score": confidence,
                "confidence_reason": reason,
                "extracted_clean_title": clean_title,
                "notes": candidate.get("notes") or f"Score: {confidence}/100 ({reason}). Confirm details before adding.",
            })
            known_pending_ids.add(c_id)
            sent_to_review += 1
            print(f"  [QUEUE-REVIEW] Score {confidence} ({reason}): '{video_title}'")

    if not dry_run:
        PENDING_PATH.write_text(json.dumps(pending_list, ensure_ascii=False, indent=2), encoding="utf-8")
        if auto_added > 0 or auto_updated > 0:
            ANIME_PATH.write_text(json.dumps(anime_data, ensure_ascii=False, indent=2), encoding="utf-8")
            subprocess.run([sys.executable, str(ROOT / "scripts" / "sort_dataset.py")], check=True)

    print(
        f"\nAuto-Sync complete: {auto_added} new anime added, {auto_updated} existing updated, "
        f"{sent_to_review} routed to review queue. Total pending: {len(pending_list)}."
    )
    return auto_added, auto_updated, sent_to_review


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto sync Hindi & regional anime dub releases.")
    parser.add_argument("--dry-run", action="store_true", help="Inspect without modifying files.")
    args = parser.parse_args()

    auto_sync(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
