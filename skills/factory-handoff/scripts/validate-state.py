#!/usr/bin/env python3
"""Validate canonical Factory state front matter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


ALLOWED_FIELDS = {
    "schema_version", "project_slug", "branch_slug", "task_key", "objective",
    "task_revision", "status", "current_lifecycle", "last_checkpointed_lifecycle",
    "latest_handoff", "change_assurance_report", "proof_ledger", "git_head",
    "git_branch", "worktree_dirty", "pending_transition", "active_assignment",
    "active_attempt", "attempted_model_tiers", "stale_artifacts",
    "checkpoint_sequence", "latest_snapshot", "route_sequence",
    "latest_route_record", "updated_at",
}
REQUIRED_FIELDS = {
    "schema_version", "project_slug", "branch_slug", "objective", "task_revision",
    "status", "current_lifecycle", "checkpoint_sequence", "route_sequence", "updated_at",
}
STATUSES = {"lifecycle_active", "lifecycle_checkpointed", "terminal"}
LIFECYCLES = {
    "INTAKE", "CONTEXT_GATHERING", "REPLICATION", "ANALYSIS", "PLANNING",
    "IMPLEMENTATION", "REVIEW", "VIDEO_EVIDENCE", "VERIFICATION", "DELIVERY",
    "AWAITING_INPUT", "COMPLETED", "CANCELLED",
}


def read_front_matter(path: Path) -> tuple[dict[str, object], bool]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("state must start with YAML front matter")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError("state front matter is not closed") from error
    has_narrative = any(line.strip() for line in lines[end + 1 :])
    document = yaml.safe_load("\n".join(lines[1:end]))
    if not isinstance(document, dict):
        raise ValueError("state front matter must be an object")
    return document, has_narrative


def validate(document: dict[str, object], allow_legacy: bool) -> list[str]:
    if "schema_version" not in document:
        return [] if allow_legacy else ["legacy state has no schema_version and requires migration"]
    errors: list[str] = []
    unknown = sorted(set(document) - ALLOWED_FIELDS)
    if unknown:
        errors.append(f"unknown fields: {', '.join(unknown)}")
    missing = sorted(REQUIRED_FIELDS - set(document))
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")
    if document.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if document.get("status") not in STATUSES:
        errors.append(f"status must be one of {sorted(STATUSES)}")
    if document.get("current_lifecycle") not in LIFECYCLES:
        errors.append("current_lifecycle is not a Factory lifecycle")
    for field in ("task_revision", "checkpoint_sequence", "route_sequence"):
        value = document.get(field)
        minimum = 1 if field == "task_revision" else 0
        if not isinstance(value, int) or value < minimum:
            errors.append(f"{field} must be an integer of at least {minimum}")
    if not isinstance(document.get("worktree_dirty"), (bool, type(None))):
        errors.append("worktree_dirty must be boolean or null")
    if not isinstance(document.get("attempted_model_tiers", []), list):
        errors.append("attempted_model_tiers must be a list")
    if not isinstance(document.get("stale_artifacts", []), list):
        errors.append("stale_artifacts must be a list")
    if document.get("status") == "terminal" and document.get("current_lifecycle") not in {"COMPLETED", "CANCELLED"}:
        errors.append("terminal state requires COMPLETED or CANCELLED")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state")
    parser.add_argument("--allow-legacy", action="store_true")
    args = parser.parse_args()
    path = Path(args.state)
    try:
        document, has_narrative = read_front_matter(path)
        if has_narrative and not (args.allow_legacy and "schema_version" not in document):
            raise ValueError("state must contain front matter only")
        errors = validate(document, args.allow_legacy)
    except (OSError, ValueError, yaml.YAMLError) as error:
        errors = [str(error)]
    if errors:
        for error in errors:
            print(f"{path}: {error}", file=sys.stderr)
        return 1
    print(f"Factory state is valid: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
