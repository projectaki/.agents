#!/usr/bin/env python3
"""Resolve a shared repository task path and discover separate legacy records."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def git(repository: Path, *arguments: str) -> str | None:
    result = subprocess.run(["git", "-C", str(repository), *arguments], text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else None


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", value.replace("/", "--").lower()).strip(".-") or "unknown"


def repository_identity(repository: Path) -> tuple[Path, str]:
    common = git(repository, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not common:
        return repository.resolve(), slugify(repository.resolve().name)
    shared = Path(common).resolve()
    worktrees = git(repository, "worktree", "list", "--porcelain") or ""
    primary = next((line.removeprefix("worktree ") for line in worktrees.splitlines() if line.startswith("worktree ")), str(shared))
    return shared, slugify(Path(primary).name.removesuffix(".git"))


def resolve(repository: Path, database: Path) -> dict[str, object]:
    identity, project = repository_identity(repository)
    branch = git(repository, "symbolic-ref", "--quiet", "--short", "HEAD")
    if not branch:
        revision = git(repository, "rev-parse", "--short", "HEAD")
        branch = f"detached-{revision}" if revision else "no-branch"
    branch_slug = slugify(branch)
    canonical = database / project / branch_slug
    legacy = []
    unresolved = []
    for candidate in sorted(database.glob(f"*/{branch_slug}/task.json")):
        if candidate.parent == canonical:
            continue
        try:
            document = json.loads(candidate.read_text(encoding="utf-8"))
            recorded_repository = Path(document["repository"])
            stored_identity = document.get("repository_identity")
            if stored_identity == str(identity) or recorded_repository.is_dir() and repository_identity(recorded_repository)[0] == identity:
                legacy.append(str(candidate.parent))
            elif not recorded_repository.is_dir() and stored_identity is None:
                unresolved.append(str(candidate.parent))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return {"repository_identity": str(identity), "task_root": str(canonical), "legacy_task_roots": legacy, "unresolved_task_roots": unresolved}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discover", action="store_true", help="Print canonical and matching legacy locations as JSON")
    args = parser.parse_args()
    result = resolve(Path.cwd(), Path.home() / ".agents-db")
    if args.discover:
        print(json.dumps(result))
    else:
        print(result["task_root"])
        for legacy in result["legacy_task_roots"]:
            print(f"Existing records remain at {legacy}; inspect them before creating a separate task.", file=sys.stderr)
        for unresolved in result["unresolved_task_roots"]:
            print(f"Unverified records for this branch remain at {unresolved}; the recorded repository is unavailable.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
