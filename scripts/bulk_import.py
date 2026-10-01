"""Merge a batch of manually researched dub entries into anime.json.

For platforms with no automatable feed (Sony YAY!, JioHotstar, Anime
Times, Netflix...) - prepare a text file with one dub per line:

    Title | Date | Status | Platform

Date accepts either "YYYY-MM-DD" or "Mon DD, YYYY". Status is one of
Finished/Airing/Removed/TBA. Example line:

    Jujutsu Kaisen (Season 1) | Oct 09, 2025 | Finished | JioHotstar

Usage:
    python scripts/bulk_import.py path/to/batch.txt

Titles are matched against existing anime.json entries using the same
normalization the dataset was originally built with (so "Dandadan" and
"Dan Da Dan" merge, and a bare title matches "(Season 1)"). A match gets
a new dub appended to its hindi_dubs list; no match creates a new entry.
Re-sorts and renumbers ids automatically when done - see sort_dataset.py.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "src" / "aninidhi" / "data" / "anime.json"


def normalize_key(title: str) -> str:
    t = title.lower()
    t = t.replace("dandadan", "dan da dan")
    t = t.replace("\u2013", "-").replace("\u2019", "'")
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s*\(?season\s*1\)?\s*$", "", t).strip()
    return t


def parse_date(raw: str) -> str:
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {raw!r}")


def parse_batch_file(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 4:
            print(f"Skipping malformed line (need 4 fields): {line!r}", file=sys.stderr)
            continue
        title, date_raw, status, platform = parts
        rows.append({
            "title": title,
            "release_date": parse_date(date_raw),
            "status": status,
            "platform": platform,
            "media_type": "movie" if "(movie)" in title.lower() else "series",
        })
    return rows


def blank_entry(next_id: int, title: str) -> dict:
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
        "hindi_available": True,
        "hindi_dubs": [],
        "notes": None,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/bulk_import.py path/to/batch.txt", file=sys.stderr)
        return 1

    batch_path = Path(sys.argv[1])
    if not batch_path.exists():
        print(f"File not found: {batch_path}", file=sys.stderr)
        return 1

    rows = parse_batch_file(batch_path)
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    by_key = {normalize_key(a["title"]): a for a in data}
    next_id = max((a["id"] for a in data), default=0) + 1

    added_dubs, new_entries, skipped_dupes = 0, 0, 0

    for row in rows:
        key = normalize_key(row["title"])
        anime = by_key.get(key)

        if anime is None:
            anime = blank_entry(next_id, row["title"])
            next_id += 1
            data.append(anime)
            by_key[key] = anime
            new_entries += 1

        already_has = any(
            d["platform"] == row["platform"] and d["release_date"] == row["release_date"]
            for d in anime["hindi_dubs"]
        )
        if already_has:
            skipped_dupes += 1
            continue

        anime["hindi_dubs"].append({
            "platform": row["platform"],
            "release_date": row["release_date"],
            "status": row["status"],
            "media_type": row["media_type"],
        })
        anime["hindi_available"] = True
        added_dubs += 1

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Processed {len(rows)} rows: {new_entries} new anime entries, "
        f"{added_dubs} dubs added, {skipped_dupes} exact duplicates skipped."
    )
    subprocess.run([sys.executable, str(ROOT / "scripts" / "sort_dataset.py")], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
