"""Re-sort anime.json so entries read oldest-to-latest by most recent dub date,
and renumber `id` to match that order (id 1 = oldest, highest id = newest).

Run this after adding entries by hand, or it runs automatically in auto_sync
and review_candidates.

Usage:
    python scripts/sort_dataset.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "src" / "aninidhi" / "data" / "anime.json"


def newest_dub_date(anime: dict) -> tuple:
    dubs = list(anime.get("hindi_dubs", []))
    for d in anime.get("dubs", []):
        if d not in dubs:
            dubs.append(d)
    dates = [str(d["release_date"]).strip() for d in dubs if d.get("release_date")]
    if not dates:
        return (0, "")
    iso_dates = [d for d in dates if re.match(r"^\d{4}", d)]
    if iso_dates:
        return (1, max(iso_dates))
    return (2, max(dates))


def main() -> int:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    data.sort(key=newest_dub_date)
    for i, anime in enumerate(data, start=1):
        anime["id"] = i
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Sorted {len(data)} entries, oldest dub first. IDs renumbered 1-{len(data)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
