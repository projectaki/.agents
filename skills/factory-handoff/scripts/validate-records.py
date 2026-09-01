#!/usr/bin/env python3
"""Validate compact canonical Factory records."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from records import validate_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_root", type=Path)
    args = parser.parse_args()
    errors = validate_root(args.task_root.expanduser().resolve())
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Factory records are valid: {args.task_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
