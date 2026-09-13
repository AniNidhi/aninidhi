"""Command-line interface for aninidhi."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, List

from . import (
    get_by_platform,
    get_dub_info,
    get_latest,
    list_all,
    multi_platform_dubs,
    platform_stats,
    refresh,
    search,
)


def _print_table(entries: List[dict[str, Any]]) -> None:
    if not entries:
        print("No matching anime found.")
        return
    for a in entries:
        dubs = a.get("hindi_dubs") or []
        if dubs:
            parts = ", ".join(f"{d['platform']} ({d['release_date']})" for d in dubs)
            print(f"- {a.get('title')}  [{parts}]")
        else:
            print(f"- {a.get('title')}  [no Hindi dub yet]")


def _print_info(entries: List[dict[str, Any]]) -> None:
    if not entries:
        print("No matching anime found.")
        return
    for a in entries:
        print(f"\n{a.get('title')}")
        dubs = a.get("hindi_dubs") or []
        if not dubs:
            print("  No Hindi dub yet.")
            continue
        for d in sorted(dubs, key=lambda d: d["release_date"]):
            print(f"  - {d['platform']}: {d['release_date']} ({d.get('status', 'Unknown')})")


def build_parser() -> argparse.ArgumentParser:
    json_flag = argparse.ArgumentParser(add_help=False)
    json_flag.add_argument(
        "--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS
    )

    parser = argparse.ArgumentParser(
        prog="aninidhi", description="Track which anime have official Hindi dubs."
    )
    parser.add_argument("--json", action="store_true", default=False, help="print raw JSON instead of a table")
    sub = parser.add_subparsers(dest="command", required=True)

    p_latest = sub.add_parser("latest", help="most recently Hindi-dubbed anime", parents=[json_flag])
    p_latest.add_argument("-n", "--limit", type=int, default=10)

    p_search = sub.add_parser("search", help="search anime by title", parents=[json_flag])
    p_search.add_argument("query")

    p_info = sub.add_parser(
        "info", help="full per-platform dub breakdown for a title", parents=[json_flag]
    )
    p_info.add_argument("query")

    p_platform = sub.add_parser(
        "platform", help="Hindi-dubbed anime on a given platform", parents=[json_flag]
    )
    p_platform.add_argument("name")

    sub.add_parser("all", help="list every known anime entry", parents=[json_flag])
    sub.add_parser("multi", help="anime dubbed on 2+ platforms", parents=[json_flag])
    sub.add_parser("stats", help="dub count per platform", parents=[json_flag])

    p_refresh = sub.add_parser("refresh", help="pull the latest dataset from the source URL")
    p_refresh.add_argument("--url", default=None, help="override ANINIDHI_SOURCE_URL")

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "latest":
        results = get_latest(limit=args.limit)
    elif args.command == "search":
        results = search(args.query)
    elif args.command == "info":
        results = get_dub_info(args.query)
        if not args.json:
            _print_info(results)
            return 0
    elif args.command == "platform":
        results = get_by_platform(args.name)
    elif args.command == "all":
        results = list_all()
    elif args.command == "multi":
        results = multi_platform_dubs()
    elif args.command == "stats":
        stats = platform_stats()
        if args.json:
            print(json.dumps(stats, ensure_ascii=False, indent=2))
        else:
            for platform, count in sorted(stats.items(), key=lambda kv: -kv[1]):
                print(f"- {platform}: {count}")
        return 0
    elif args.command == "refresh":
        try:
            count = refresh(url=args.url, force=True)
        except Exception as exc:
            print(f"Refresh failed: {exc}", file=sys.stderr)
            return 1
        print(f"Refreshed {count} entries.")
        return 0
    else:
        parser.print_help()
        return 1

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        _print_table(results)
    return 0


def run(argv: List[str] | None = None) -> int:
    """Entry point used by the installed `aninidhi` console script."""
    try:
        return main(argv)
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        return 1


if __name__ == "__main__":
    sys.exit(run())