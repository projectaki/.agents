#!/usr/bin/env python3
"""Validate lifecycle-independent Factory work-skill contracts."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


WORK_SKILLS = (
    "factory-intake",
    "factory-triage",
    "factory-implement",
    "factory-assure",
    "factory-draft-pr",
)

REQUIRED_HEADINGS = (
    "Purpose",
    "Inputs",
    "Operation",
    "Outputs",
    "Side effects",
    "Failure results",
    "Non-goals",
)

FORBIDDEN_PATTERNS = {
    "orchestration branch": re.compile(r"\bwhen orchestrated\b", re.IGNORECASE),
    "orchestrator role": re.compile(r"\bprimary thread\b|\brouted worker\b", re.IGNORECASE),
    "handoff dependency": re.compile(r"\bfactory-handoff\b", re.IGNORECASE),
    "telemetry dependency": re.compile(r"\bfactory-telemetry\b|\bbest-effort writer\b", re.IGNORECASE),
    "handoff file": re.compile(
        r"`(?:task\.json|assurance\.json|report\.md|history\.jsonl)`",
        re.IGNORECASE,
    ),
    "lifecycle control": re.compile(
        r"\b(?:start|spawn|advance|route to) (?:another|the next) lifecycle\b",
        re.IGNORECASE,
    ),
}


def markdown_body(text: str) -> str:
    parts = text.split("---", maxsplit=2)
    return parts[2] if len(parts) == 3 else text


def validate_contract(text: str) -> list[str]:
    body = markdown_body(text)
    errors: list[str] = []
    heading_positions: list[int] = []

    for heading in REQUIRED_HEADINGS:
        matches = list(re.finditer(rf"^## {re.escape(heading)}$", body, re.MULTILINE))
        if len(matches) != 1:
            errors.append(f"required heading {heading!r} must appear exactly once")
            continue
        heading_positions.append(matches[0].start())

    if len(heading_positions) == len(REQUIRED_HEADINGS):
        if heading_positions != sorted(heading_positions):
            errors.append("required contract headings must appear in contract order")

    for description, pattern in FORBIDDEN_PATTERNS.items():
        match = pattern.search(body)
        if match:
            errors.append(f"{description} is not allowed: {match.group(0)}")

    return errors


def validate_skill(skill_directory: Path) -> list[str]:
    skill_file = skill_directory / "SKILL.md"
    try:
        text = skill_file.read_text(encoding="utf-8")
    except OSError as error:
        return [f"cannot read {skill_file}: {error}"]
    return validate_contract(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "skills_root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Directory that contains the Factory skill directories",
    )
    args = parser.parse_args()

    errors: list[str] = []
    for skill_name in WORK_SKILLS:
        for error in validate_skill(args.skills_root / skill_name):
            errors.append(f"{skill_name}: {error}")

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print("Factory work-step contracts are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
