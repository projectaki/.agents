#!/usr/bin/env python3
"""Validate mechanical readability rules for a lifecycle human report."""

from __future__ import annotations

import re
import sys
from pathlib import Path

INTERNAL_ID = re.compile(r"\b[HPSRUVGE]\d+\b")
FORBIDDEN_PHRASES = (
    "faithful port",
    "divergent decision point",
    "contract delta",
    "evidence plane",
)
COUNT_AGGREGATE = re.compile(
    r"\b\d+\s+(?:endpoints?|routes?|jobs?|consumers?|commands?|transitions?)\b",
    re.IGNORECASE,
)


def table_column_count(line: str) -> int:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return 0
    return len(re.split(r"(?<!\\)\|", stripped)) - 2


def validate(report_path: Path) -> list[str]:
    text = report_path.read_text(encoding="utf-8")
    errors: list[str] = []
    in_mermaid = False

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_mermaid:
                in_mermaid = False
            elif stripped[3:].strip().lower() == "mermaid":
                in_mermaid = True
            continue

        id_match = INTERNAL_ID.search(line)
        if id_match:
            errors.append(
                f"line {line_number}: replace internal ID {id_match.group()!r} "
                "with its plain-language meaning"
            )

        lowered = line.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                errors.append(
                    f"line {line_number}: replace prohibited jargon {phrase!r}"
                )

        columns = table_column_count(line)
        if columns > 4:
            errors.append(
                f"line {line_number}: Markdown table has {columns} columns; "
                "use at most 4 or restructure it"
            )

        if in_mermaid:
            aggregate_match = COUNT_AGGREGATE.search(line)
            if aggregate_match:
                errors.append(
                    f"line {line_number}: replace count-based diagram node "
                    f"{aggregate_match.group()!r} with named items or a list"
                )

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate-human-report.py <report.md>", file=sys.stderr)
        return 2

    report_path = Path(sys.argv[1])
    if not report_path.is_file():
        print(f"human report not found: {report_path}", file=sys.stderr)
        return 2

    errors = validate(report_path)
    if errors:
        for error in errors:
            print(f"{report_path}: {error}", file=sys.stderr)
        return 1

    print(f"Human report is valid: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
