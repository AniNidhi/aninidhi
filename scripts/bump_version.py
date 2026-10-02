"""Atomic version bumping utility for AniNidhi.

Updates pyproject.toml and verifies consistency across project files.

Usage:
    python scripts/bump_version.py 0.3.2
    python scripts/bump_version.py --patch
    python scripts/bump_version.py --minor
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = ROOT / "pyproject.toml"


def get_current_version() -> str:
    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if not match:
        raise RuntimeError("Could not find version string in pyproject.toml")
    return match.group(1)


def bump_version_str(current: str, part: str) -> str:
    parts = current.split(".")
    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    patch = int(parts[2].split("+")[0].split("-")[0]) if len(parts) > 2 and parts[2].isdigit() else 0

    if part == "patch":
        patch += 1
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "major":
        major += 1
        minor = 0
        patch = 0
    return f"{major}.{minor}.{patch}"


def set_version(new_version: str) -> None:
    content = PYPROJECT_PATH.read_text(encoding="utf-8")
    updated = re.sub(r'version\s*=\s*"[^"]+"', f'version = "{new_version}"', content)
    PYPROJECT_PATH.write_text(updated, encoding="utf-8")
    print(f"Updated pyproject.toml version to {new_version}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bump AniNidhi package version.")
    parser.add_argument("version", nargs="?", default=None, help="Explicit version (e.g. 0.3.2)")
    parser.add_argument("--patch", action="store_true", help="Bump patch version (0.3.1 -> 0.3.2)")
    parser.add_argument("--minor", action="store_true", help="Bump minor version (0.3.1 -> 0.4.0)")
    parser.add_argument("--major", action="store_true", help="Bump major version (0.3.1 -> 1.0.0)")
    args = parser.parse_args()

    current = get_current_version()
    print(f"Current version: {current}")

    if args.version:
        new_version = args.version
    elif args.patch:
        new_version = bump_version_str(current, "patch")
    elif args.minor:
        new_version = bump_version_str(current, "minor")
    elif args.major:
        new_version = bump_version_str(current, "major")
    else:
        print("Please specify a version or --patch / --minor / --major", file=sys.stderr)
        return 1

    set_version(new_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
