from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "src" / "aninidhi" / "data" / "anime.json"
ANILIST_URL = "https://graphql.anilist.co"

QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
    id
    genres
    episodes
    description(asHtml: false)
    coverImage { large }
    studios(isMain: true) { nodes { name } }
  }
}
"""


def base_title(title: str) -> str:
    return re.sub(r"\s*[\(\-–][^)]*(season|cour|part|ova|movie|special)[^)]*\)?\s*$", "", title, flags=re.I).strip()


def clean_synopsis(text: str | None) -> str | None:
    if not text:
        return None
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500]


def query_anilist(title: str) -> dict | None:
    payload = json.dumps({"query": QUERY, "variables": {"search": title}}).encode("utf-8")
    req = urllib.request.Request(
        ANILIST_URL, data=payload, headers={"Content-Type": "application/json", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read())
    return (body.get("data") or {}).get("Media")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--delay", type=float, default=1.5)
    args = parser.parse_args()

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    todo = [a for a in data if not a.get("anilist_id")]
    if args.limit:
        todo = todo[: args.limit]

    print(f"{len(todo)} records to enrich (of {len(data)} total).")
    updated = 0

    for i, anime in enumerate(todo, 1):
        query_title = base_title(anime["title"])
        try:
            media = query_anilist(query_title)
        except Exception as exc:
            print(f"[{i}/{len(todo)}] FAILED  {anime['title']!r}: {exc}", file=sys.stderr)
            time.sleep(args.delay)
            continue

        if not media:
            print(f"[{i}/{len(todo)}] no match  {anime['title']!r} (searched {query_title!r})")
            time.sleep(args.delay)
            continue

        anime["anilist_id"] = media.get("id")
        anime["anilist_url"] = f"https://anilist.co/anime/{media['id']}" if media.get("id") else None
        if not anime.get("genres"):
            anime["genres"] = media.get("genres") or []
        if anime.get("episodes") is None:
            anime["episodes"] = media.get("episodes")
        if not anime.get("synopsis"):
            anime["synopsis"] = clean_synopsis(media.get("description"))
        if not anime.get("poster_url"):
            anime["poster_url"] = (media.get("coverImage") or {}).get("large")
        studios = (media.get("studios") or {}).get("nodes") or []
        if not anime.get("studio") and studios:
            anime["studio"] = studios[0].get("name")

        print(f"[{i}/{len(todo)}] matched   {anime['title']!r} -> AniList #{media.get('id')}")
        updated += 1
        time.sleep(args.delay)

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDone. Updated {updated}, no-match/failed {len(todo) - updated}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())