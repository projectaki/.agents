#!/usr/bin/env python3
"""Validate canonical Factory checkpoints, routes, dispositions, and counts."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from history_records import counts, load_records


COUNT_LINE = re.compile(
    r"Counts: checkpoints (?P<checkpoints>\d+) \| routes (?P<routes>\d+) \| "
    r"rework loops (?P<rework>\d+) \| rejected routes (?P<rejected>\d+)"
)


def validate_timeline(task_root: Path, expected: dict[str, int]) -> list[str]:
    timeline_path = task_root / "history" / "timeline.md"
    if not timeline_path.exists():
        return [f"{timeline_path}: timeline is missing"]
    match = COUNT_LINE.search(timeline_path.read_text(encoding="utf-8"))
    if not match:
        return [f"{timeline_path}: canonical count line is missing"]
    actual = {name: int(value) for name, value in match.groupdict().items()}
    return [
        f"{timeline_path}: {name} count is {actual[name]}, expected {value}"
        for name, value in expected.items()
        if actual[name] != value
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_root")
    parser.add_argument("--skip-timeline", action="store_true")
    args = parser.parse_args()
    task_root = Path(args.task_root)
    checkpoints, routes, errors = load_records(task_root)
    expected = counts(checkpoints, routes)
    if not args.skip_timeline:
        errors.extend(validate_timeline(task_root, expected))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(
        "Factory history is valid: "
        f"{expected['checkpoints']} checkpoints, {expected['routes']} routes, "
        f"{expected['rework']} rework loops, {expected['rejected']} rejected routes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
