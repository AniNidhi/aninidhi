"""Remove a specific anime entry from anime.json entirely.

For removing something that shouldn't be tracked at all - added by
mistake, wrong match during review, or anything else that needs to come
out of the dataset completely (not just skipped in the pending queue,
which is what review_candidates.py's [s]kip option is for).

Usage:
    python scripts/remove_entry.py "title or partial title"
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "src" / "aninidhi" / "data" / "anime.json"


def main() -> int:
    if len(sys.argv) != 2:
        print('Usage: python scripts/remove_entry.py "title or partial title"', file=sys.stderr)
        return 1

    query = sys.argv[1].strip().lower()
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    matches = [a for a in data if query in a["title"].lower()]

    if not matches:
        print(f"No entry matching {sys.argv[1]!r} found.")
        return 1

    print(f"{len(matches)} match(es):")
    for i, a in enumerate(matches, 1):
        dubs = ", ".join(f"{d['platform']} ({d['release_date']})" for d in a["hindi_dubs"])
        print(f"  {i}. {a['title']}  [{dubs}]")

    choice = input("Remove which number? (or 'c' to cancel): ").strip().lower()
    if choice == "c":
        print("Cancelled, nothing removed.")
        return 0

    try:
        target = matches[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice, nothing removed.", file=sys.stderr)
        return 1

    confirm = input(f"Really remove {target['title']!r}? (y/N): ").strip().lower()
    if confirm != "y":
        print("Cancelled, nothing removed.")
        return 0

    data.remove(target)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Removed {target['title']!r}.")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "sort_dataset.py")], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
