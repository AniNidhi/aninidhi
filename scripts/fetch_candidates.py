from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PENDING_PATH = ROOT / "pending_review.json"

CHANNEL_HANDLE = "Muse_HindiDub"
API_BASE = "https://www.googleapis.com/youtube/v3"


def api_get(endpoint: str, params: dict) -> dict:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("Set YOUTUBE_API_KEY first.", file=sys.stderr)
        sys.exit(1)
    url = f"{API_BASE}/{endpoint}?{urllib.parse.urlencode({**params, 'key': api_key})}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read())


def get_uploads_playlist_id(handle: str) -> str:
    data = api_get("channels", {"part": "contentDetails", "forHandle": f"@{handle}"})
    items = data.get("items") or []
    if not items:
        raise RuntimeError(f"No channel found for handle @{handle}")
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def get_recent_uploads(playlist_id: str, max_results: int = 25) -> list[dict]:
    data = api_get(
        "playlistItems",
        {"part": "snippet", "playlistId": playlist_id, "maxResults": max_results},
    )
    return data.get("items") or []


def load_pending() -> list[dict]:
    if PENDING_PATH.exists():
        return json.loads(PENDING_PATH.read_text(encoding="utf-8"))
    return []


def main() -> int:
    pending = load_pending()
    known_ids = {entry["video_id"] for entry in pending}

    playlist_id = get_uploads_playlist_id(CHANNEL_HANDLE)
    uploads = get_recent_uploads(playlist_id)

    new_count = 0
    for item in uploads:
        snippet = item["snippet"]
        video_id = snippet["resourceId"]["videoId"]
        if video_id in known_ids:
            continue
        pending.append({
            "video_id": video_id,
            "video_title": snippet["title"],
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "published_at": snippet["publishedAt"],
            "source": f"youtube:{CHANNEL_HANDLE}",
            "status": "needs_review",
            "notes": "Confirm episode-vs-trailer, match or add an anime.json entry.",
        })
        new_count += 1

    PENDING_PATH.write_text(json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Found {new_count} new candidate(s). Total pending: {len(pending)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())