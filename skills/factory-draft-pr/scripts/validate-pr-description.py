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

EXPECTED_ENTRY_FIELDS = [
    "Affected surface",
    "Evidence",
    "Verdict",
    "Residual risk or waiver",
]
ALLOWED_SURFACES = {"Data", "Component", "System"}
EVIDENCE_PREFIXES = ("Automated — ", "Inspection — ")
FIELD_LINE = re.compile(r"^- \*\*([^*]+):\*\* (.+)$")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)")
PINNED_FILE_PERMALINK = re.compile(
    r"https://github\.com/[^/]+/[^/]+/blob/[0-9a-fA-F]{40}/[^)\s]+"
)
WAIVER_ACCEPTOR = re.compile(
    r"\b(?:I|the [A-Za-z][A-Za-z -]{1,60}) accepted\b|"
    r"\baccepted by [A-Za-z][A-Za-z -]{1,60}\b",
    re.IGNORECASE,
)
UNPROVEN_GAP = re.compile(
    r"\b(?:unproven|unverified|untested|not proven|not verified|not tested|"
    r"does not prove|do not prove|cannot prove|no (?:automated )?test|"
    r"not covered)\b",
    re.IGNORECASE,
)
WAIVER_REASON = re.compile(r"\b(?:because|due to)\b", re.IGNORECASE)

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


def trim_blank_lines(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def split_regression_entries(lines: list[str]) -> tuple[list[list[str]], list[str]]:
    errors: list[str] = []
    separator_indexes = [
        index for index, line in enumerate(lines) if line.strip() == "---"
    ]

    for index in separator_indexes:
        if (
            index == 0
            or index == len(lines) - 1
            or lines[index - 1].strip()
            or lines[index + 1].strip()
        ):
            errors.append(
                "Regression assurance entry separators must be a blank line, "
                "'---', and a blank line"
            )

    visible_lines = trim_blank_lines(lines)
    if visible_lines and visible_lines[-1].strip() == "---":
        errors.append("Regression assurance must not have a rule after the last entry")

    entries: list[list[str]] = []
    start = 0
    for index in separator_indexes:
        entries.append(trim_blank_lines(lines[start:index]))
        start = index + 1
    entries.append(trim_blank_lines(lines[start:]))

    if any(not entry for entry in entries):
        errors.append("Regression assurance separators must appear only between entries")

    return [entry for entry in entries if entry], errors


def validate_regression_entry(lines: list[str], number: int) -> list[str]:
    errors: list[str] = []
    field_start = next(
        (index for index, line in enumerate(lines) if line.startswith("- **")),
        None,
    )
    if field_start is None:
        return [f"Regression assurance entry {number} has no labeled fields"]

    behavior_block = lines[:field_start]
    if not behavior_block or behavior_block[-1].strip():
        errors.append(
            f"Regression assurance entry {number} needs a blank line between "
            "the behavior paragraph and its fields"
        )
        behavior_lines = behavior_block
    else:
        behavior_lines = behavior_block[:-1]

    if not behavior_lines or any(not line.strip() for line in behavior_lines):
        errors.append(
            f"Regression assurance entry {number} must start with one behavior paragraph"
        )
    if any(re.match(r"\s*(?:#{1,6}\s|[-*+]\s|>\s|```)", line) for line in behavior_lines):
        errors.append(
            f"Regression assurance entry {number} behavior must not have a heading or list marker"
        )

    field_lines = lines[field_start:]
    if len(field_lines) != len(EXPECTED_ENTRY_FIELDS):
        errors.append(
            f"Regression assurance entry {number} must have exactly 4 labeled fields"
        )

    values: dict[str, str] = {}
    for index, expected_label in enumerate(EXPECTED_ENTRY_FIELDS):
        if index >= len(field_lines):
            break
        match = FIELD_LINE.fullmatch(field_lines[index])
        if not match or match.group(1) != expected_label:
            errors.append(
                f"Regression assurance entry {number} field {index + 1} must be "
                f"'- **{expected_label}:** <value>'"
            )
            continue
        values[expected_label] = match.group(2)

    surface = values.get("Affected surface")
    if surface and surface not in ALLOWED_SURFACES:
        errors.append(
            f"Regression assurance entry {number} affected surface must be "
            "Data, Component, or System"
        )

    evidence = values.get("Evidence")
    if evidence:
        if not evidence.startswith(EVIDENCE_PREFIXES):
            errors.append(
                f"Regression assurance entry {number} evidence must start with "
                "'Automated — ' or 'Inspection — '"
            )
        links = MARKDOWN_LINK.findall(evidence)
        if not links:
            errors.append(
                f"Regression assurance entry {number} evidence requires at least "
                "1 commit-pinned file permalink"
            )
        for link in links:
            if not PINNED_FILE_PERMALINK.fullmatch(link):
                errors.append(
                    f"Regression assurance entry {number} evidence link is not a "
                    f"commit-pinned file permalink: {link}"
                )

    verdict = values.get("Verdict")
    if verdict and verdict not in {"Pass", "Waiver accepted"}:
        errors.append(
            f"Regression assurance entry {number} verdict must be exactly "
            "'Pass' or 'Waiver accepted'"
        )

    residual_risk = values.get("Residual risk or waiver")
    if verdict == "Waiver accepted" and residual_risk:
        if residual_risk == "None":
            errors.append(
                f"Regression assurance entry {number} waiver must describe the unproven gap"
            )
        else:
            if not WAIVER_ACCEPTOR.search(residual_risk):
                errors.append(
                    f"Regression assurance entry {number} waiver must say who accepted it"
                )
            if not UNPROVEN_GAP.search(residual_risk):
                errors.append(
                    f"Regression assurance entry {number} waiver must name what is unproven"
                )
            if not WAIVER_REASON.search(residual_risk):
                errors.append(
                    f"Regression assurance entry {number} waiver must say why it was accepted"
                )

    return errors


def validate_regression_entries(lines: list[str]) -> list[str]:
    if any(line.strip().startswith("|") for line in lines):
        return ["Regression assurance must use stacked entries, not a table"]

    entries, errors = split_regression_entries(lines)
    if not entries:
        return [*errors, "Regression assurance must contain at least 1 entry"]

    for number, entry in enumerate(entries, start=1):
        errors.extend(validate_regression_entry(entry, number))
    return errors


def validate(text: str) -> list[str]:
    lines = text.splitlines()
    _, bodies, errors = section_bodies(lines)

    if "<!--" in text or "-->" in text:
        errors.append("template comments and placeholders must be removed")

    if bodies:
        errors.extend(validate_regression_entries(bodies["Regression assurance"]))

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
