#!/usr/bin/env python3
"""Append one compact Factory checkpoint and guarded route decision."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from records import LIFECYCLES, digest, git_facts, load_history, load_json, validate_assurance, validate_task
from routing import decide


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--task-root", required=True, type=Path)
    value.add_argument("--lifecycle", required=True)
    value.add_argument("--outcome", required=True)
    value.add_argument("--reason", required=True)
    value.add_argument("--assignment-id")
    value.add_argument("--attempt", type=int)
    value.add_argument("--worker-tier", choices=["fast", "standard", "high"])
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if not args.reason.strip():
            raise ValueError("reason must be nonempty text")
        if args.attempt is not None and args.attempt < 1:
            raise ValueError("attempt must be a positive integer")
        task_root = args.task_root.expanduser().resolve()
        task_path = task_root / "task.json"
        report_path = task_root / "report.md"
        assurance_path = task_root / "assurance.json"
        history_path = task_root / "history.jsonl"

        task = load_json(task_path)
        errors = validate_task(task)
        if args.lifecycle not in LIFECYCLES:
            errors.append(f"unknown lifecycle: {args.lifecycle}")
        if not report_path.exists() or not report_path.read_text(encoding="utf-8").strip():
            errors.append("report.md must contain current human-readable text")
        assurance = load_json(assurance_path) if assurance_path.exists() else None
        if assurance is not None:
            errors.extend(validate_assurance(assurance, int(task["task_revision"])))
        if errors:
            raise ValueError("; ".join(errors))

        history, history_errors = load_history(history_path)
        if history_errors:
            raise ValueError("; ".join(history_errors))
        repository = Path(task["repository"])
        git_head, git_branch, worktree_dirty = git_facts(repository)
        decision = decide(
            task,
            assurance,
            history,
            args.lifecycle,
            args.outcome,
            git_head=git_head,
            worktree_dirty=worktree_dirty,
        )
        status = "terminal" if args.lifecycle in {"COMPLETED", "CANCELLED"} else (
            "awaiting_input" if decision.next_lifecycle == "AWAITING_INPUT" else "checkpointed"
        )
        record = {
            "schema_version": 1,
            "sequence": len(history) + 1,
            "occurred_at": utc_now(),
            "lifecycle": args.lifecycle,
            "outcome": args.outcome,
            "reason": args.reason.strip(),
            "next_lifecycle": decision.next_lifecycle,
            "stop": decision.stop,
            "route_reason": decision.reason,
            "resume_lifecycle": decision.resume_lifecycle,
            "status": status,
            "task_revision": task["task_revision"],
            "continuation_mode": task["continuation_mode"],
            "assignment_id": args.assignment_id,
            "attempt": args.attempt,
            "worker_tier": args.worker_tier,
            "git_head": git_head,
            "git_branch": git_branch,
            "worktree_dirty": worktree_dirty,
            "task_sha256": digest(task_path),
            "assurance_sha256": digest(assurance_path) if assurance_path.exists() else None,
            "report_sha256": digest(report_path),
        }
        task_root.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(history_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8", closefd=True) as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        print(json.dumps({
            "checkpoint": record["sequence"],
            "next_lifecycle": decision.next_lifecycle,
            "stop": decision.stop,
            "reason": decision.reason,
        }, separators=(",", ":")))
        return 0
    except Exception as error:
        print(f"Factory checkpoint failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
