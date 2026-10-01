"""Re-sort anime.json so entries read oldest-to-latest by most recent dub date,
and renumber `id` to match that order (id 1 = oldest, highest id = newest).

Run this after adding entries by hand, or it runs automatically at the end
of scripts/review_candidates.py.

Usage:
    python scripts/sort_dataset.py
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "src" / "aninidhi" / "data" / "anime.json"


def newest_dub_date(anime: dict) -> str:
    dates = [d["release_date"] for d in anime.get("hindi_dubs", []) if d.get("release_date")]
    return max(dates) if dates else ""


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
