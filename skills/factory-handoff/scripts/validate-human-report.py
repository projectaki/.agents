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
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")
WORD = re.compile(r"\b[\w'-]+\b")
STATUS_ROW = re.compile(r"^\|\s*(?:\*\*)?status(?:\*\*)?\s*\|", re.IGNORECASE)
REQUIRED_HEADINGS = ("## At a glance", "## Remaining risk", "## Next action")


def table_column_count(line: str) -> int:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return 0
    return len(re.split(r"(?<!\\)\|", stripped)) - 2


def validate(report_path: Path) -> list[str]:
    text = report_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    errors: list[str] = []
    in_mermaid = False
    in_code_fence = False
    paragraph_lines: list[str] = []
    paragraph_start = 0
    consecutive_list_items = 0
    table_blocks = 0
    previous_line_was_table = False
    has_non_table_visual = False

    nonempty_lines = [line.strip() for line in lines if line.strip()]
    if not nonempty_lines or not nonempty_lines[0].startswith("# "):
        errors.append("line 1: start the report with one level-1 outcome heading")

    for heading in REQUIRED_HEADINGS:
        if heading.lower() not in {line.lower() for line in nonempty_lines}:
            errors.append(f"missing required heading {heading!r}")

    first_lines = {line.lower() for line in nonempty_lines[:12]}
    if "## at a glance" not in first_lines:
        errors.append("put '## At a glance' within the first 12 nonempty lines")

    if not any(STATUS_ROW.search(line.strip()) for line in lines):
        errors.append("add a Status row to the At a glance table")

    def finish_paragraph() -> None:
        nonlocal paragraph_lines, paragraph_start
        if not paragraph_lines:
            return
        word_count = len(WORD.findall(" ".join(paragraph_lines)))
        if word_count > 100:
            errors.append(
                f"line {paragraph_start}: paragraph has {word_count} words; "
                "use at most 100"
            )
        paragraph_lines = []
        paragraph_start = 0

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            finish_paragraph()
            if not in_code_fence:
                has_non_table_visual = True
                in_code_fence = True
            else:
                in_code_fence = False
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
        if columns:
            finish_paragraph()
            if not previous_line_was_table:
                table_blocks += 1
            previous_line_was_table = True
        else:
            previous_line_was_table = False

        if columns > 4:
            errors.append(
                f"line {line_number}: Markdown table has {columns} columns; "
                "use at most 4 or restructure it"
            )

        if re.search(r"!\[[^\]]*\]\([^)]+\)", line):
            has_non_table_visual = True

        if LIST_ITEM.match(line):
            finish_paragraph()
            consecutive_list_items += 1
            if consecutive_list_items == 9:
                errors.append(
                    f"line {line_number}: list has more than 8 consecutive items; "
                    "group or summarize it"
                )
        elif stripped:
            consecutive_list_items = 0

        is_plain_text = (
            stripped
            and not in_code_fence
            and not stripped.startswith(("#", "|", ">"))
            and not LIST_ITEM.match(line)
        )
        if is_plain_text:
            if not paragraph_lines:
                paragraph_start = line_number
            paragraph_lines.append(stripped)
        elif not stripped or stripped.startswith(("#", ">")):
            finish_paragraph()

        if in_mermaid:
            aggregate_match = COUNT_AGGREGATE.search(line)
            if aggregate_match:
                errors.append(
                    f"line {line_number}: replace count-based diagram node "
                    f"{aggregate_match.group()!r} with named items or a list"
                )

    finish_paragraph()

    word_count = len(WORD.findall(text))
    if word_count > 500:
        errors.append(f"report has {word_count} words; use at most 500")
    if word_count > 250 and table_blocks < 2 and not has_non_table_visual:
        errors.append(
            "reports longer than 250 words need a table, diagram, image, or "
            "code example in addition to the At a glance table"
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
