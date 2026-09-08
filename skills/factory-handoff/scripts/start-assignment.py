#!/usr/bin/env python3
"""Validate a selected stage and record its execution start."""

from __future__ import annotations

import argparse
import fcntl
import json
import sys
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from prerequisites import prerequisite_errors
from records import changed_files, git_base_revision, git_facts, load_history, load_json, validate_root, validate_task
from runtime import emit, finish_assignment
from transaction import replace_text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-root", required=True, type=Path)
    parser.add_argument("--lifecycle", required=True, choices=["INTAKE", "TRIAGE", "PLAN_ASSURANCE", "IMPLEMENTATION", "CHANGE_ASSURANCE", "DELIVERY"])
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--model")
    parser.add_argument("--reasoning-effort")
    parser.add_argument("--interrupt", action="store_true", help="Close an interrupted assignment before starting a replacement")
    args = parser.parse_args()
    root = args.task_root.expanduser().resolve()
    try:
        if not args.worker_id.strip() or not args.reason.strip():
            raise ValueError("Worker identity and routing reason must be nonempty")
        with (root / ".checkpoint.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if (root / "pending-checkpoint.json").exists():
                raise ValueError("Recover the pending checkpoint before dispatch")
            task = load_json(root / "task.json")
            history, errors = load_history(root / "history.jsonl")
            errors.extend(validate_task(task))
            if history:
                errors.extend(validate_root(root))
            if history and (history[-1].get("status") == "terminal" or history[-1].get("next_lifecycle") == "AWAITING_INPUT"):
                errors.append("Resolve the pause or reopen completion before dispatch.")
            assurance = load_json(root / "assurance.json") if (root / "assurance.json").exists() else None
            repository = Path(task["repository"])
            head, branch, dirty = git_facts(repository)
            base = git_base_revision(repository, task.get("base_ref"))
            errors.extend(prerequisite_errors(task, assurance, history, args.lifecycle, worker_id=args.worker_id,
                          git_head=head, git_base=base, files=changed_files(repository, base, head) if base and head else None,
                          git_branch=branch, worktree_dirty=dirty))
            if args.lifecycle == "IMPLEMENTATION" and dirty is not False:
                errors.append("Implementation requires a clean starting worktree.")
            run_id = args.run_id or str(uuid.uuid4())
            run = [item for item in history if item.get("run_id") == run_id]
            if task["continuation_mode"] == "automatic" and sum(item.get("active_seconds") or 0 for item in run) >= 1800:
                errors.append("The automatic run has exhausted its active-time allowance.")
            if run and (run[-1].get("stop") or task["continuation_mode"] == "supervised"):
                errors.append("A continued run identity cannot resume a closed execution; start a new run.")
            if errors:
                raise ValueError("; ".join(errors))
            active = root / "assignment.json"
            if active.exists() and history:
                previous = load_json(active)
                if previous.get("assignment_id") == history[-1].get("assignment_id"):
                    finish_assignment(root, history[-1])
            if active.exists():
                if not args.interrupt:
                    raise ValueError("An assignment is already active; resume it or explicitly interrupt it")
                previous = load_json(active)
                if previous["run_id"] == run_id:
                    raise ValueError("A replacement after interruption requires a new run identity")
                emit(root, "actor_interrupted", run_id=previous["run_id"], assignment_id=previous["assignment_id"], invocation_id=previous["assignment_id"], worker_id=previous["worker_id"])
                emit(root, "run_interrupted", run_id=previous["run_id"])
            assignment = dict(run_id=run_id, assignment_id=str(uuid.uuid4()), lifecycle=args.lifecycle,
                              worker_id=args.worker_id, reason=args.reason,
                              task_revision=task["task_revision"], sequence=len(history),
                              started_at=datetime.now(timezone.utc).isoformat(),
                              timeout_seconds=max(1, 1800 - sum(item.get("active_seconds") or 0 for item in run))
                              if task["continuation_mode"] == "automatic" else None)
            replace_text(active, json.dumps(assignment))
            if not run:
                source = Path(__file__).resolve().parents[3]
                revision = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True)
                status = subprocess.run(["git", "-C", str(source), "status", "--porcelain"], capture_output=True, text=True)
                factory_revision = revision.stdout.strip() + ("-modified" if status.stdout.strip() else "") if revision.returncode == 0 else None
                emit(root, "run_started", run_id=run_id, factory_revision=factory_revision)
            emit(root, "actor_dispatched", run_id=run_id, assignment_id=assignment["assignment_id"],
                 invocation_id=assignment["assignment_id"], worker_id=args.worker_id, lifecycle=args.lifecycle, model=args.model, reasoning_effort=args.reasoning_effort)
            print(json.dumps(assignment))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"Factory dispatch failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
