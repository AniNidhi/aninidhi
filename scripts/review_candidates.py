"""Interactively review pending_review.json: accept, reject, or skip each candidate.

Supports regional language dubs (Hindi, Tamil, Telugu, etc.), TV channels (Sony YAY!, Zee Cafe, etc.),
and broadcast medium (TV, OTT, YouTube).

Usage:
    python scripts/review_candidates.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANIME_PATH = ROOT / "src" / "aninidhi" / "data" / "anime.json"
PENDING_PATH = ROOT / "pending_review.json"


def load(path: Path) -> list:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def save(path: Path, data: list) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def find_similar(anime_data: list, title_guess: str) -> list[dict]:
    needle = title_guess.strip().lower()
    return [a for a in anime_data if needle in a["title"].lower() or a["title"].lower() in needle]


def prompt(text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or (default or "")


def add_dub_to_existing(anime: dict, candidate: dict) -> None:
    detected_lang = (candidate.get("detected_languages") or ["Hindi"])[0]
    language = prompt("Language", default=detected_lang)
    platform = prompt("Platform/Channel")
    medium = prompt("Medium (TV/OTT/YouTube)", default=candidate.get("medium", "OTT"))
    date = prompt("Release date (YYYY-MM-DD)")
    status = prompt("Status", default="Finished")

    dub_entry = {
        "language": language,
        "platform": platform,
        "medium": medium,
        "release_date": date,
        "status": status,
        "media_type": "series",
    }

    anime.setdefault("dubs", []).append(dub_entry)

    if language.lower() == "hindi":
        anime.setdefault("hindi_dubs", []).append({
            "platform": platform,
            "release_date": date,
            "status": status,
            "media_type": "series",
        })
        anime["hindi_available"] = True


def create_new_entry(anime_data: list, title: str, candidate: dict) -> dict:
    detected_lang = (candidate.get("detected_languages") or ["Hindi"])[0]
    language = prompt("Language", default=detected_lang)
    platform = prompt("Platform/Channel")
    medium = prompt("Medium (TV/OTT/YouTube)", default=candidate.get("medium", "OTT"))
    date = prompt("Release date (YYYY-MM-DD)")
    status = prompt("Status", default="Finished")
    next_id = max((a["id"] for a in anime_data), default=0) + 1

    dub_entry = {
        "language": language,
        "platform": platform,
        "medium": medium,
        "release_date": date,
        "status": status,
        "media_type": "series",
    }

    is_hindi = language.lower() == "hindi"
    hindi_dubs = [{
        "platform": platform,
        "release_date": date,
        "status": status,
        "media_type": "series",
    }] if is_hindi else []

    return {
        "id": next_id,
        "title": title,
        "original_title": None,
        "genres": [],
        "season": None,
        "season_year": None,
        "episodes": None,
        "studio": None,
        "synopsis": None,
        "poster_url": None,
        "mal_id": None,
        "mal_url": None,
        "anilist_id": None,
        "anilist_url": None,
        "imdb_id": None,
        "imdb_url": None,
        "imdb_rating": None,
        "hindi_available": is_hindi,
        "hindi_dubs": hindi_dubs,
        "dubs": [dub_entry],
        "notes": None,
    }


def main() -> int:
    anime_data = load(ANIME_PATH)
    pending = load(PENDING_PATH)
    remaining = []
    changed = False

    for entry in pending:
        if entry.get("status") != "needs_review":
            remaining.append(entry)
            continue

        print(f"\n{entry['video_title']}")
        print(f"  {entry['video_url']}  (published {entry['published_at']})")
        if entry.get("notes"):
            print(f"  {entry['notes']}")

        matches = find_similar(anime_data, entry["video_title"])
        if matches:
            print("  Possible existing match(es):")
            for i, m in enumerate(matches, 1):
                print(f"    {i}. {m['title']}")

        choice = prompt(
            "  [a]ccept new / [m]atch existing / [r]eject / [s]kip for now", default="s"
        ).lower()

        if choice == "r":
            changed = True
            continue  # drop it
        if choice == "s":
            remaining.append(entry)
            continue
        if choice == "m" and matches:
            idx = int(prompt("  Which match number?", default="1")) - 1
            add_dub_to_existing(matches[idx], entry)
            changed = True
            continue
        if choice == "a":
            if entry.get("is_lineup") or "lineup" in entry["video_title"].lower():
                print("\n  ⚠️ WARNING: This item looks like a Lineup / Multi-Anime article.")
                print("  Instead of accepting the article title directly, please enter the actual specific anime title below.")
            title = prompt("  Clean anime title", default=entry["video_title"])
            anime_data.append(create_new_entry(anime_data, title, entry))
            changed = True
            continue

        remaining.append(entry)

    save(PENDING_PATH, remaining)
    if changed:
        save(ANIME_PATH, anime_data)
        subprocess.run([sys.executable, str(ROOT / "scripts" / "sort_dataset.py")], check=True)

    print(f"\n{len(remaining)} still pending, {len(pending) - len(remaining)} handled this session.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
