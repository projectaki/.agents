"""Shared validation and file helpers for compact Factory records."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


LIFECYCLES = {
    "INTAKE",
    "TRIAGE",
    "PLAN_ASSURANCE",
    "IMPLEMENTATION",
    "CHANGE_ASSURANCE",
    "DELIVERY",
    "AWAITING_INPUT",
    "COMPLETED",
    "CANCELLED",
}
SIGNALS = {
    "impact",
    "uncertainty",
    "reasoning_difficulty",
    "proof_difficulty",
    "input_gaps",
}
LOW_RISK_CHECKS = {
    "clear_requirements",
    "clean_worktree",
    "localized_reversible",
    "established_pattern",
    "deterministic_proof",
    "low_impact",
    "low_uncertainty",
    "low_reasoning_difficulty",
    "low_proof_difficulty",
    "no_input_gaps",
    "no_sensitive_change",
}
ROUTING_FLAGS = {
    "decision_required",
    "scope_changed",
    "risk_changed",
    "required_dependency_unavailable",
}
AUTHORITY_FIELDS = {"edit", "test", "commit", "push", "draft_pull_request"}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_facts(repository: Path) -> tuple[str | None, str | None, bool | None]:
    def run(*arguments: str) -> str | None:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            text=True,
            capture_output=True,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    head = run("rev-parse", "HEAD")
    branch = run("symbolic-ref", "--quiet", "--short", "HEAD")
    status = run("status", "--porcelain")
    return head, branch, bool(status) if status is not None else None


def require_text(value: object, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be nonempty text")


def require_text_list(value: object, field: str, errors: list[str], *, nonempty: bool = False) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        errors.append(f"{field} must be a text list")
    elif nonempty and not value:
        errors.append(f"{field} must not be empty")


def validate_task(task: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if task.get("schema_version") != 1:
        errors.append("task.schema_version must be 1")
    revision = task.get("task_revision")
    if not isinstance(revision, int) or revision < 1:
        errors.append("task.task_revision must be a positive integer")
    if task.get("status") not in {"aligned", "needs_input"}:
        errors.append("task.status must be aligned or needs_input")
    repository = task.get("repository")
    require_text(repository, "task.repository", errors)
    if isinstance(repository, str) and not Path(repository).is_absolute():
        errors.append("task.repository must be an absolute path")
    elif isinstance(repository, str) and not Path(repository).is_dir():
        errors.append("task.repository must be an accessible directory")
    require_text(task.get("objective"), "task.objective", errors)
    require_text_list(task.get("acceptance_criteria"), "task.acceptance_criteria", errors, nonempty=True)
    scope = task.get("scope")
    if not isinstance(scope, dict):
        errors.append("task.scope must be an object")
    else:
        require_text_list(scope.get("included"), "task.scope.included", errors)
        require_text_list(scope.get("excluded"), "task.scope.excluded", errors)
    authority = task.get("authority")
    if not isinstance(authority, dict) or set(authority) != AUTHORITY_FIELDS:
        errors.append(f"task.authority must contain exactly {sorted(AUTHORITY_FIELDS)}")
    elif any(not isinstance(value, bool) for value in authority.values()):
        errors.append("every task.authority value must be boolean")
    if task.get("deliverable") not in {"local_commit", "draft_pull_request"}:
        errors.append("task.deliverable must be local_commit or draft_pull_request")
    if task.get("continuation_mode") not in {"supervised", "automatic"}:
        errors.append("task.continuation_mode must be supervised or automatic")
    require_text_list(task.get("open_decisions"), "task.open_decisions", errors)
    return errors


def validate_assurance(assurance: dict[str, Any], task_revision: int) -> list[str]:
    errors: list[str] = []
    if assurance.get("schema_version") != 1:
        errors.append("assurance.schema_version must be 1")
    if assurance.get("task_revision") != task_revision:
        errors.append("assurance.task_revision must match task.task_revision")
    if assurance.get("risk_class") not in {"low", "medium", "high"}:
        errors.append("assurance.risk_class must be low, medium, or high")
    signals = assurance.get("signals")
    if not isinstance(signals, dict) or set(signals) != SIGNALS:
        errors.append(f"assurance.signals must contain exactly {sorted(SIGNALS)}")
    elif any(value not in {"low", "medium", "high"} for value in signals.values()):
        errors.append("every assurance signal must be low, medium, or high")
    gate = assurance.get("low_risk_gate")
    if not isinstance(gate, dict) or not isinstance(gate.get("eligible"), bool):
        errors.append("assurance.low_risk_gate must contain boolean eligible")
    else:
        checks = gate.get("checks")
        if not isinstance(checks, dict) or set(checks) != LOW_RISK_CHECKS:
            errors.append(
                f"assurance.low_risk_gate.checks must contain exactly {sorted(LOW_RISK_CHECKS)}"
            )
        elif any(not isinstance(value, bool) for value in checks.values()):
            errors.append("every low-risk check must be boolean")
        elif gate["eligible"] and not all(checks.values()):
            errors.append("low-risk eligibility requires every check to pass")
    if not isinstance(assurance.get("plan_assurance_required"), bool):
        errors.append("assurance.plan_assurance_required must be boolean")
    if not isinstance(assurance.get("sensitive_change"), bool):
        errors.append("assurance.sensitive_change must be boolean")
    elif assurance["sensitive_change"] and assurance.get("plan_assurance_required") is not True:
        errors.append("a sensitive change requires plan assurance")
    if (
        assurance.get("risk_class") == "high"
        or isinstance(signals, dict) and "high" in signals.values()
    ) and assurance.get("plan_assurance_required") is not True:
        errors.append("high risk or a high signal requires plan assurance")
    for field in ("paths", "risks", "diff_groups", "evidence", "exceptions", "blockers"):
        if not isinstance(assurance.get(field), list):
            errors.append(f"assurance.{field} must be a list")
    for field in ("base_revision", "change_revision"):
        if assurance.get(field) is not None and not isinstance(assurance.get(field), str):
            errors.append(f"assurance.{field} must be text or null")
    if assurance.get("verdict") not in {
        "unverified",
        "plan_approved",
        "plan_rejected",
        "pass",
        "fail",
        "blocked",
    }:
        errors.append("assurance.verdict is invalid")
    routing = assurance.get("routing")
    if not isinstance(routing, dict) or set(routing) != ROUTING_FLAGS:
        errors.append(f"assurance.routing must contain exactly {sorted(ROUTING_FLAGS)}")
    elif any(not isinstance(value, bool) for value in routing.values()):
        errors.append("every assurance.routing value must be boolean")
    return errors


def load_history(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.exists():
        return records, errors
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError("record is not an object")
            if record.get("sequence") != line_number:
                raise ValueError("sequence does not match line number")
            if record.get("schema_version") != 1:
                raise ValueError("schema_version must be 1")
            datetime.fromisoformat(str(record.get("occurred_at", "")).replace("Z", "+00:00"))
            if record.get("lifecycle") not in LIFECYCLES:
                raise ValueError("unknown lifecycle")
            next_lifecycle = record.get("next_lifecycle")
            if next_lifecycle is not None and next_lifecycle not in LIFECYCLES:
                raise ValueError("unknown next_lifecycle")
            if record.get("status") not in {"checkpointed", "awaiting_input", "terminal"}:
                raise ValueError("invalid status")
            if record.get("continuation_mode") not in {"supervised", "automatic"}:
                raise ValueError("invalid continuation_mode")
            if not isinstance(record.get("task_revision"), int) or record["task_revision"] < 1:
                raise ValueError("invalid task_revision")
            if record.get("stop") not in {True, False}:
                raise ValueError("stop must be boolean")
            records.append(record)
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            errors.append(f"history line {line_number}: {error}")
    return records, errors


def validate_root(task_root: Path) -> list[str]:
    errors: list[str] = []
    task_path = task_root / "task.json"
    report_path = task_root / "report.md"
    history_path = task_root / "history.jsonl"
    try:
        task = load_json(task_path)
        errors.extend(validate_task(task))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return [f"{task_path}: {error}"]

    records, history_errors = load_history(history_path)
    errors.extend(history_errors)
    if not records:
        errors.append("history.jsonl must contain at least one checkpoint")
        return errors

    latest = records[-1]
    if latest.get("task_revision") != task.get("task_revision"):
        errors.append("latest history task revision does not match task.json")
    if latest.get("task_sha256") != digest(task_path):
        errors.append("task.json changed after the latest checkpoint")
    if not report_path.exists():
        errors.append("report.md does not exist")
    elif latest.get("report_sha256") != digest(report_path):
        errors.append("report.md changed after the latest checkpoint")

    assurance_path = task_root / "assurance.json"
    expected_assurance_hash = latest.get("assurance_sha256")
    if assurance_path.exists():
        try:
            assurance = load_json(assurance_path)
            errors.extend(validate_assurance(assurance, int(task["task_revision"])))
            if expected_assurance_hash != digest(assurance_path):
                errors.append("assurance.json changed after the latest checkpoint")
        except (OSError, json.JSONDecodeError, ValueError) as error:
            errors.append(f"{assurance_path}: {error}")
    elif expected_assurance_hash is not None:
        errors.append("latest history references missing assurance.json")

    if latest.get("status") == "terminal" and latest.get("lifecycle") not in {"COMPLETED", "CANCELLED"}:
        errors.append("terminal status requires COMPLETED or CANCELLED lifecycle")
    if latest.get("status") == "terminal" and latest.get("next_lifecycle") is not None:
        errors.append("terminal status cannot have a next lifecycle")

    repository = Path(task["repository"])
    git_head, git_branch, worktree_dirty = git_facts(repository)
    if latest.get("git_head") != git_head:
        errors.append("Git head changed after the latest checkpoint")
    if latest.get("git_branch") != git_branch:
        errors.append("Git branch changed after the latest checkpoint")
    if latest.get("worktree_dirty") != worktree_dirty:
        errors.append("Git worktree state changed after the latest checkpoint")
    return errors
