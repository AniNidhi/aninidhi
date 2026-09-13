"""Fill in imdb_id/imdb_url/imdb_rating via the OMDb API.

Requires a free key from https://www.omdbapi.com/apikey.aspx.
Untested against the live API in this environment. Run with --limit 5 first.

Usage:
    export OMDB_API_KEY=your_key_here
    python scripts/enrich_imdb.py [--limit N] [--delay SECONDS]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "src" / "aninidhi" / "data" / "anime.json"
OMDB_URL = "https://www.omdbapi.com/"


def base_title(title: str) -> str:
    return re.sub(r"\s*[\(\-–][^)]*(season|cour|part|ova|movie|special)[^)]*\)?\s*$", "", title, flags=re.I).strip()


def query_omdb(title: str, api_key: str) -> dict | None:
    params = urllib.parse.urlencode({"t": title, "apikey": api_key})
    with urllib.request.urlopen(f"{OMDB_URL}?{params}", timeout=15) as resp:
        body = json.loads(resp.read())
    if body.get("Response") == "False":
        return None
    return body


def main() -> int:
    api_key = os.environ.get("OMDB_API_KEY")
    if not api_key:
        print("Set OMDB_API_KEY first - https://www.omdbapi.com/apikey.aspx", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    todo = [a for a in data if not a.get("imdb_id")]
    if args.limit:
        todo = todo[: args.limit]

    print(f"{len(todo)} records to enrich (of {len(data)} total).")
    updated = 0

    for i, anime in enumerate(todo, 1):
        query_title = base_title(anime["title"])
        try:
            result = query_omdb(query_title, api_key)
        except Exception as exc:
            print(f"[{i}/{len(todo)}] FAILED  {anime['title']!r}: {exc}", file=sys.stderr)
            time.sleep(args.delay)
            continue

        if not result:
            print(f"[{i}/{len(todo)}] no match  {anime['title']!r} (searched {query_title!r})")
            time.sleep(args.delay)
            continue

        anime["imdb_id"] = result.get("imdbID")
        anime["imdb_url"] = f"https://www.imdb.com/title/{result['imdbID']}/" if result.get("imdbID") else None
        rating = result.get("imdbRating")
        anime["imdb_rating"] = float(rating) if rating and rating != "N/A" else None

        print(f"[{i}/{len(todo)}] matched   {anime['title']!r} -> {result.get('imdbID')}")
        updated += 1
        time.sleep(args.delay)

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDone. Updated {updated}, no-match/failed {len(todo) - updated}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())