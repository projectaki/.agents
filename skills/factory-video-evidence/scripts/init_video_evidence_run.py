#!/usr/bin/env python3
"""Create one shared evidence workspace for a Git branch."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path


AUTH_INSTRUCTIONS = """# Authentication

## Profiles

For each profile, document its role, login URL, `states/<profile>.json` file,
credential variable names, and reauthentication steps. State explicitly when a
workflow needs no authentication.
"""

AUTH_CREDENTIALS = """# Store dummy test credentials only. Never store production credentials.
# Example:
# AUTH_USERNAME=
# AUTH_PASSWORD=
"""


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


def branch_name() -> str:
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        branch = ""

    if not branch:
        raise SystemExit("Could not determine Git branch; pass --branch")
    return branch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Project label; defaults to the Git root name")
    parser.add_argument("--branch", help="Git branch; defaults to the current branch")
    parser.add_argument(
        "--base",
        type=Path,
        default=Path.home() / "evidence",
        help="Evidence root outside the repository (default: ~/evidence)",
    )
    return parser.parse_args()


def create_private_file(path: Path, content: str) -> None:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return

    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        file.write(content)


def main() -> None:
    args = parse_args()
    project = slug(args.project or project_name())
    branch = slug(args.branch or branch_name())
    project_root = args.base.expanduser().resolve() / project
    auth_root = project_root / "_auth"
    state_root = auth_root / "states"
    root = project_root / branch

    state_root.mkdir(parents=True, exist_ok=True)
    os.chmod(auth_root, 0o700)
    os.chmod(state_root, 0o700)
    create_private_file(auth_root / "instructions.md", AUTH_INSTRUCTIONS)
    create_private_file(auth_root / "credentials.env", AUTH_CREDENTIALS)

    for relative in ("workflows", "publish"):
        (root / relative).mkdir(parents=True, exist_ok=True)

    print(root)


if __name__ == "__main__":
    main()
