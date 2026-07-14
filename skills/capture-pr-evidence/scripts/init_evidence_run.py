#!/usr/bin/env python3
"""Create a secret-safe temporary workspace for PR evidence."""

from __future__ import annotations

import argparse
import os
import re
import secrets
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
    parser.add_argument("--run", help="Thread or run label; defaults to a unique timestamp")
    parser.add_argument(
        "--base",
        type=Path,
        default=Path(os.environ.get("TMPDIR", "/tmp")) / "codex-pr-evidence",
        help="Evidence root outside the repository",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project = slug(args.project or project_name())
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = slug(args.run or f"{timestamp}-{secrets.token_hex(3)}")
    root = args.base.expanduser().resolve() / project / run

    for relative in ("private", "working", "publish/screenshots", "publish/videos"):
        (root / relative).mkdir(parents=True, exist_ok=False)

    os.chmod(root / "private", 0o700)
    print(root)


if __name__ == "__main__":
    main()
