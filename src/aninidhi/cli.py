"""Command-line interface for aninidhi."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, List

from . import (
    get_airing,
    get_by_language,
    get_by_medium,
    get_by_platform,
    get_dub_info,
    get_latest,
    get_series_info,
    get_upcoming,
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
        dubs = a.get("dubs") or a.get("hindi_dubs") or []
        status_tag = f" [{a.get('status')}]" if a.get("status") else ""
        if dubs:
            parts = ", ".join(
                f"{d.get('language', 'Hindi')}: {d['platform']} ({d['release_date']})"
                + (f" [{d['medium']}]" if d.get("medium") else "")
                for d in dubs
            )
            print(f"- {a.get('title')}{status_tag}  [{parts}]")
        else:
            print(f"- {a.get('title')}{status_tag}  [no dub tracked yet]")


def _print_latest_table(entries: List[dict[str, Any]]) -> None:
    if not entries:
        print("No matching anime found.")
        return
    for a in entries:
        dubs = a.get("dubs") or a.get("hindi_dubs") or []
        status_tag = f" [{a.get('status')}]" if a.get("status") else ""
        if dubs:
            newest = max(dubs, key=lambda d: str(d.get("release_date", "")))
            lang = newest.get("language", "Hindi")
            med = f" ({newest['medium']})" if newest.get("medium") else ""
            print(f"- {a.get('title')}{status_tag}  [{lang} Dub | {newest['platform']}{med} ({newest.get('release_date', 'N/A')})]")
        else:
            print(f"- {a.get('title')}{status_tag}  [no dub tracked yet]")


def _print_info(entries: List[dict[str, Any]]) -> None:
    if not entries:
        print("No matching anime found.")
        return
    for a in entries:
        status_badge = f" [{a.get('status')}]" if a.get("status") else ""
        print(f"\n{a.get('title')}{status_badge}")
        dubs = a.get("dubs") or a.get("hindi_dubs") or []
        if not dubs:
            print("  No dub tracked yet.")
            continue
        for d in sorted(dubs, key=lambda d: str(d.get("release_date", ""))):
            lang = d.get("language", "Hindi")
            med = f" [{d['medium']}]" if d.get("medium") else ""
            ep_str = f" ({d['episodes']})" if d.get("episodes") else ""
            print(f"  - [{lang}] {d['platform']}{med}: {d.get('release_date', 'N/A')} ({d.get('status', 'Finished')}){ep_str}")


def _print_series(series_info: dict[str, Any]) -> None:
    if not series_info.get("seasons"):
        print(f"No series matches found for '{series_info.get('query')}'.")
        return
    print(f"\nSeries: {series_info.get('series_title')} [{series_info.get('overall_status')}]")
    print(f"Total Seasons/Entries: {series_info.get('total_entries')}")
    if series_info.get("airing_seasons"):
        print(f"Currently Airing: {', '.join(series_info['airing_seasons'])}")
    print("\nSeasons & Dub Platforms Breakdown:")
    for s in series_info.get("seasons", []):
        print(f"  - {s['title']} [{s['status']}]")
        dubs = s.get("dubs") or s.get("hindi_dubs", [])
        for d in dubs:
            lang = d.get("language", "Hindi")
            med = f" [{d['medium']}]" if d.get("medium") else ""
            print(f"      • [{lang}] {d['platform']}{med}: {d.get('release_date', 'N/A')} ({d.get('status', 'Finished')})")


def build_parser() -> argparse.ArgumentParser:
    json_flag = argparse.ArgumentParser(add_help=False)
    json_flag.add_argument(
        "--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS
    )

    parser = argparse.ArgumentParser(
        prog="aninidhi", description="Track official Indian regional and Hindi anime dubs."
    )
    parser.add_argument("--json", action="store_true", default=False, help="print raw JSON instead of a table")
    sub = parser.add_subparsers(dest="command", required=True)

    p_latest = sub.add_parser("latest", help="most recently dubbed anime", parents=[json_flag])
    p_latest.add_argument("-n", "--limit", type=int, default=10)
    p_latest.add_argument("-l", "--language", type=str, default=None, help="filter by language (Hindi, Tamil, Telugu, etc.)")

    p_upcoming = sub.add_parser("upcoming", help="scheduled or announced upcoming dubs", parents=[json_flag])
    p_upcoming.add_argument("-l", "--language", type=str, default=None, help="filter by language (Hindi, Tamil, Telugu, etc.)")

    p_search = sub.add_parser("search", help="search anime by title", parents=[json_flag])
    p_search.add_argument("query", nargs="+", help="anime title query")

    p_info = sub.add_parser(
        "info", help="full per-platform dub breakdown for a title", parents=[json_flag]
    )
    p_info.add_argument("query", nargs="+", help="anime title query")

    p_series = sub.add_parser(
        "series", help="complete season breakdown and airing status for a series", parents=[json_flag]
    )
    p_series.add_argument("query", nargs="+", help="series title query")

    sub.add_parser("airing", help="list anime currently Airing", parents=[json_flag])

    p_platform = sub.add_parser(
        "platform", help="dubbed anime on a given platform or TV channel", parents=[json_flag]
    )
    p_platform.add_argument("name", nargs="+", help="platform/channel name")

    p_lang = sub.add_parser(
        "language", help="dubbed anime in a given language (Hindi, Tamil, Telugu, etc.)", parents=[json_flag]
    )
    p_lang.add_argument("name", help="language name")

    p_medium = sub.add_parser(
        "medium", help="dubbed anime on a given medium (TV, OTT, YouTube)", parents=[json_flag]
    )
    p_medium.add_argument("name", help="medium name (TV, OTT, YouTube)")

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
        results = get_latest(limit=args.limit, language=getattr(args, "language", None))
        if not args.json:
            _print_latest_table(results)
            return 0
    elif args.command == "upcoming":
        results = get_upcoming(language=getattr(args, "language", None))
        if not args.json:
            _print_table(results)
            return 0
    elif args.command == "search":
        query_str = " ".join(args.query)
        results = search(query_str)
    elif args.command == "info":
        query_str = " ".join(args.query)
        results = get_dub_info(query_str)
        if not args.json:
            _print_info(results)
            return 0
    elif args.command == "series":
        query_str = " ".join(args.query)
        info = get_series_info(query_str)
        if args.json:
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            _print_series(info)
        return 0
    elif args.command == "airing":
        results = get_airing()
    elif args.command == "platform":
        platform_str = " ".join(args.name)
        results = get_by_platform(platform_str)
    elif args.command == "language":
        results = get_by_language(args.name)
    elif args.command == "medium":
        results = get_by_medium(args.name)
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
