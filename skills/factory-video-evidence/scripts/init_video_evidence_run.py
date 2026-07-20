#!/usr/bin/env python3
"""Create a local workspace for UI workflow scripts and published videos."""

from __future__ import annotations

import argparse
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._")
    return normalized.lower() or "project"


def project_name() -> str:
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return Path(root).name
    except (FileNotFoundError, subprocess.CalledProcessError):
        return Path.cwd().name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Project label; defaults to the Git root name")
    parser.add_argument(
        "--thread",
        required=True,
        help="Agent thread name used to group related evidence runs",
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=Path.home() / "evidence",
        help="Evidence root outside the repository (default: ~/evidence)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project = slug(args.project or project_name())
    thread = slug(args.thread)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    root = args.base.expanduser().resolve() / project / thread / timestamp

    for relative in ("workflows", "publish"):
        (root / relative).mkdir(parents=True, exist_ok=False)

    print(root)


if __name__ == "__main__":
    main()
