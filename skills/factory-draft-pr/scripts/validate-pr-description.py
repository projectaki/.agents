#!/usr/bin/env python3
"""Check required Factory PR content, evidence links, and publication read-back."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_SECTIONS = {"What changed", "Blast radius", "Regression assurance"}
REQUIRED_FIELDS = {"Affected surface", "Evidence", "Verdict", "Residual risk or waiver"}
FIELD_LINE = re.compile(r"^\s*[-*]\s+\*\*([^*]+):\*\*\s*(.*)$")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)")
PINNED_FILE_PERMALINK = re.compile(
    r"https://github\.com/[^/]+/[^/]+/blob/[0-9a-fA-F]{40}/[^)\s]+"
)


def validate_regression_entry(text: str, number: int) -> list[str]:
    errors: list[str] = []
    fields: dict[str, str] = {}
    behavior: list[str] = []
    for line in text.splitlines():
        match = FIELD_LINE.fullmatch(line)
        if match:
            label, value = match.groups()
            if label in fields:
                errors.append(f"Entry {number} repeats {label}")
            fields[label] = value.strip()
        elif line.strip() and not fields:
            behavior.append(line.strip())
    if not behavior:
        errors.append(f"Entry {number} must identify the behavior")
    for label in sorted(REQUIRED_FIELDS):
        if not fields.get(label):
            errors.append(f"Entry {number} requires {label}")

    evidence = fields.get("Evidence", "")
    links = MARKDOWN_LINK.findall(evidence)
    if not links:
        errors.append(f"Entry {number} requires at least 1 commit-pinned file permalink")
    for link in links:
        if not PINNED_FILE_PERMALINK.fullmatch(link):
            errors.append(f"Entry {number} evidence link is not a commit-pinned file permalink: {link}")

    verdict = fields.get("Verdict", "").casefold()
    if verdict not in {"pass", "waiver accepted"}:
        errors.append(f"Entry {number} verdict must be Pass or Waiver accepted")
    if verdict == "waiver accepted" and fields.get("Residual risk or waiver", "").casefold() == "none":
        errors.append(f"Entry {number} requires the accepted gap and approval reference")
    return errors


def validate(text: str) -> list[str]:
    errors: list[str] = []
    sections: dict[str, list[str]] = {}
    current: list[str] = []
    for line in text.splitlines():
        heading = re.fullmatch(r"##\s+(.+)", line.strip())
        if heading:
            name = heading.group(1).strip()
            if name in sections:
                errors.append(f"Repeated section: {name}")
            current = sections.setdefault(name, [])
        else:
            current.append(line)
    for name in sorted(REQUIRED_SECTIONS):
        if not "\n".join(sections.get(name, [])).strip():
            errors.append(f"Required section is missing or empty: {name}")
    if "<!--" in text or "-->" in text:
        errors.append("Remove template comments and placeholders")

    regression = "\n".join(sections.get("Regression assurance", []))
    entries = [entry.strip() for entry in re.split(r"(?m)^\s*---\s*$", regression) if entry.strip()]
    for number, entry in enumerate(entries, start=1):
        errors.extend(validate_regression_entry(entry, number))
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
