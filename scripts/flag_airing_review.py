from __future__ import annotations

import json
from pathlib import Path

ANIME_PATH = Path(__file__).resolve().parent.parent / "src" / "aninidhi" / "data" / "anime.json"


def main() -> int:
    data = json.loads(ANIME_PATH.read_text(encoding="utf-8"))
    airing = []
    for anime in data:
        for dub in anime.get("hindi_dubs", []):
            if dub.get("status") == "Airing":
                airing.append((anime["title"], dub["platform"], dub["release_date"]))

    airing.sort(key=lambda row: row[2])
    print(f"{len(airing)} dub(s) still marked Airing - review and update status by hand:\n")
    for title, platform, date in airing:
        print(f"- {title} [{platform}, started {date}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())