#!/usr/bin/env python3
"""Validate the deterministic, human-facing Factory PR description shape."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = [
    "What changed",
    "Blast radius",
    "Regression assurance",
]
OPTIONAL_TRAILING_SECTION = "Manual test steps"

EXPECTED_TABLE_HEADER = [
    "Behavior at risk",
    "Affected surface",
    "Evidence",
    "Verdict",
    "Residual risk or waiver",
]

INTERNAL_ID_PATTERNS = [
    re.compile(r"\bP-?\d+\b", re.IGNORECASE),
    re.compile(r"\bR-?\d+\b", re.IGNORECASE),
    re.compile(r"\bAC-?\d+\b", re.IGNORECASE),
    re.compile(r"\bF-?\d+\b", re.IGNORECASE),
    re.compile(
        r"\b(?:path|risk|finding|assignment|invocation)[-_][A-Za-z0-9_-]+\b",
        re.IGNORECASE,
    ),
]

LIFECYCLE_TERMS = re.compile(
    r"\b(?:factory lifecycle|agent lifecycle|worker assignment|model tier|"
    r"handoff checkpoint|local machine startup|test runner startup)\b",
    re.IGNORECASE,
)

THIRD_PERSON_AUTHOR_VOICE = re.compile(
    r"\b(?:the|this)\s+(?:pull\s+request\s+)?author\b|"
    r"\b(?:ask|contact|inform|notify|tell)\s+(?:the\s+)?"
    r"(?:author|developer|requester)\b|"
    r"\b(?:the|our)\s+team\s+(?:asks?|requests?|wants?)\b",
    re.IGNORECASE,
)

EVIDENCE_KINDS = {"automated", "inspection", "manual"}


def parse_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def section_bodies(lines: list[str]) -> tuple[list[str], dict[str, list[str]], list[str]]:
    errors: list[str] = []
    found: list[str] = []
    positions: dict[str, int] = {}

    for index, line in enumerate(lines):
        match = re.fullmatch(r"## (.+)", line.strip())
        if not match:
            continue
        heading = match.group(1)
        found.append(heading)
        positions[heading] = index

    allowed_sections = [
        REQUIRED_SECTIONS,
        [*REQUIRED_SECTIONS, OPTIONAL_TRAILING_SECTION],
    ]
    if found not in allowed_sections:
        errors.append(
            "level-2 sections must appear exactly once in this order: "
            + ", ".join(REQUIRED_SECTIONS)
            + f"; {OPTIONAL_TRAILING_SECTION} may appear once at the end"
        )
        return found, {}, errors

    bodies: dict[str, list[str]] = {}
    for index, heading in enumerate(found):
        start = positions[heading] + 1
        end = (
            positions[found[index + 1]]
            if index + 1 < len(found)
            else len(lines)
        )
        bodies[heading] = lines[start:end]
        visible = [
            line
            for line in bodies[heading]
            if line.strip() and not line.lstrip().startswith("<!--")
        ]
        if not visible:
            errors.append(f"{heading!r} must not be empty")

    return found, bodies, errors


def validate_regression_table(lines: list[str]) -> list[str]:
    errors: list[str] = []
    table_lines = [line for line in lines if line.strip().startswith("|")]

    if len(table_lines) < 3:
        return ["Regression assurance must contain a header and at least 1 evidence row"]

    if parse_row(table_lines[0]) != EXPECTED_TABLE_HEADER:
        errors.append("Regression assurance table header does not match the required columns")
    if parse_row(table_lines[1]) != ["---"] * len(EXPECTED_TABLE_HEADER):
        errors.append("Regression assurance table separator must contain exactly 5 columns")

    data_rows = table_lines[2:]
    for number, line in enumerate(data_rows, start=1):
        cells = parse_row(line)
        if len(cells) != len(EXPECTED_TABLE_HEADER):
            errors.append(f"Regression assurance row {number} must have 5 columns")
            continue
        if any(not cell for cell in cells):
            errors.append(f"Regression assurance row {number} contains an empty field")
        if cells[3].casefold() not in {"pass", "waiver accepted"}:
            errors.append(
                f"Regression assurance row {number} verdict must be 'Pass' or 'Waiver accepted'"
            )
        if cells[3].casefold() == "waiver accepted" and cells[4].casefold() == "none":
            errors.append(
                f"Regression assurance row {number} must describe the accepted residual risk"
            )

        evidence_parts = re.split(r"\s+[—-]\s+", cells[2], maxsplit=1)
        if len(evidence_parts) != 2 or evidence_parts[0].casefold() not in EVIDENCE_KINDS:
            errors.append(
                f"Regression assurance row {number} evidence must start with "
                "'Automated —', 'Inspection —', or 'Manual —'"
            )
            continue

        evidence_kind = evidence_parts[0].casefold()
        link_count = len(re.findall(r"\[[^\]]+\]\(https?://[^)]+\)", evidence_parts[1]))
        minimum_links = 1
        if link_count < minimum_links:
            errors.append(
                f"Regression assurance row {number} {evidence_kind} evidence "
                f"requires at least {minimum_links} durable link(s)"
            )

    return errors


def validate(text: str) -> list[str]:
    lines = text.splitlines()
    _, bodies, errors = section_bodies(lines)

    if "<!--" in text or "-->" in text:
        errors.append("template comments and placeholders must be removed")

    if bodies:
        errors.extend(validate_regression_table(bodies["Regression assurance"]))

    without_comments = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    visible_text = re.sub(
        r"\[([^\]]+)\]\(https?://[^)]+\)",
        r"\1",
        without_comments,
    )
    for pattern in INTERNAL_ID_PATTERNS:
        match = pattern.search(visible_text)
        if match:
            errors.append(f"internal ID is not allowed in the PR description: {match.group(0)}")

    match = LIFECYCLE_TERMS.search(visible_text)
    if match:
        errors.append(f"agent or machine lifecycle commentary is not allowed: {match.group(0)}")

    match = THIRD_PERSON_AUTHOR_VOICE.search(visible_text)
    if match:
        errors.append(
            "third-person author voice is not allowed in the PR description: "
            f"{match.group(0)}"
        )

    return errors


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("body", type=Path, help="Markdown file containing the PR body")
    parser.add_argument(
        "--expected",
        type=Path,
        help="Validated intended body to compare with a published read-back",
    )
    args = parser.parse_args()

    try:
        text = args.body.read_text(encoding="utf-8")
    except OSError as error:
        print(f"error: cannot read {args.body}: {error}", file=sys.stderr)
        return 2

    errors = validate(text)
    if args.expected:
        try:
            expected = args.expected.read_text(encoding="utf-8")
        except OSError as error:
            print(f"error: cannot read {args.expected}: {error}", file=sys.stderr)
            return 2
        if normalize(text) != normalize(expected):
            errors.append("published PR body does not exactly match the validated body")

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print("PR description is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
