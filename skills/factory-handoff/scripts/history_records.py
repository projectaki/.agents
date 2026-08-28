"""Shared readers and counters for canonical Factory history."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


REVIEW_VERDICTS = {"approve", "approve-with-findings", "reject", "incomplete"}
VERIFICATION_VERDICTS = {"pass", "fail", "inconclusive", "blocked"}
DISPOSITIONS = {"committed", "rejected"}


def read_front_matter(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing YAML front matter")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError("unclosed YAML front matter") from error
    document = yaml.safe_load("\n".join(lines[1:end]))
    if not isinstance(document, dict):
        raise ValueError("front matter must be an object")
    return document


def load_records(task_root: Path) -> tuple[list[tuple[Path, dict[str, Any]]], list[tuple[Path, dict[str, Any], dict[str, Any] | None]], list[str]]:
    errors: list[str] = []
    checkpoints: list[tuple[Path, dict[str, Any]]] = []
    routes: list[tuple[Path, dict[str, Any], dict[str, Any] | None]] = []

    for directory in sorted((task_root / "history" / "checkpoints").glob("[0-9]*-*")):
        manifest_path = directory / "manifest.md"
        try:
            manifest = read_front_matter(manifest_path)
            sequence = int(directory.name.split("-", 1)[0])
            if manifest.get("checkpoint_sequence") != sequence:
                errors.append(f"{manifest_path}: checkpoint sequence does not match its directory")
            if manifest.get("review_verdict") is not None and manifest["review_verdict"] not in REVIEW_VERDICTS:
                errors.append(f"{manifest_path}: invalid review_verdict {manifest['review_verdict']!r}")
            if manifest.get("verification_verdict") is not None and manifest["verification_verdict"] not in VERIFICATION_VERDICTS:
                errors.append(f"{manifest_path}: invalid verification_verdict {manifest['verification_verdict']!r}")
            checkpoints.append((manifest_path, manifest))
        except (OSError, ValueError, yaml.YAMLError) as error:
            errors.append(f"{manifest_path}: {error}")

    for directory in sorted((task_root / "history" / "routes").glob("[0-9]*-*")):
        decision_path = directory / "decision.md"
        disposition_path = directory / "disposition.md"
        try:
            decision = read_front_matter(decision_path)
            sequence = int(directory.name.split("-", 1)[0])
            if decision.get("route_sequence") != sequence:
                errors.append(f"{decision_path}: route sequence does not match its directory")
            disposition = read_front_matter(disposition_path) if disposition_path.exists() else None
            if disposition:
                if disposition.get("route_sequence") != sequence:
                    errors.append(f"{disposition_path}: route sequence does not match its directory")
                status = disposition.get("status")
                if status not in DISPOSITIONS:
                    errors.append(f"{disposition_path}: invalid status {status!r}")
                if status == "committed":
                    if disposition.get("transition_committed") is not True:
                        errors.append(f"{disposition_path}: committed route must commit its transition")
                    selected = decision.get("selected")
                    selected_to = selected.get("to") if isinstance(selected, dict) else None
                    if disposition.get("committed_lifecycle") != selected_to:
                        errors.append(f"{disposition_path}: committed lifecycle does not match the decision")
                if status == "rejected" and disposition.get("transition_committed") is not False:
                    errors.append(f"{disposition_path}: rejected route cannot commit its transition")
            routes.append((decision_path, decision, disposition))
        except (OSError, ValueError, yaml.YAMLError) as error:
            errors.append(f"{decision_path}: {error}")
    return checkpoints, routes, errors


def counts(checkpoints: list[tuple[Path, dict[str, Any]]], routes: list[tuple[Path, dict[str, Any], dict[str, Any] | None]]) -> dict[str, int]:
    rejected = sum(1 for _, _, disposition in routes if disposition and disposition.get("status") == "rejected")
    rework = sum(
        1
        for _, decision, disposition in routes
        if disposition
        and disposition.get("status") == "committed"
        and decision.get("from") == "REVIEW"
        and disposition.get("committed_lifecycle") in {"IMPLEMENTATION", "PLANNING", "ANALYSIS"}
    )
    return {"checkpoints": len(checkpoints), "routes": len(routes), "rework": rework, "rejected": rejected}
