#!/usr/bin/env python3
"""Append one compact Factory checkpoint and guarded route decision."""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from records import changed_files, digest, git_base_revision, git_facts, load_history, load_json, validate_assurance, validate_task
from routing import decide
from prerequisites import plan_fingerprint
from runtime import assignment_result, finish_assignment
from transaction import publish, recover, replace_text


OUTCOMES = {
    "INTAKE": {"aligned", "needs_input", "blocked"},
    "TRIAGE": {"ready", "needs_input", "blocked"},
    "PLAN_ASSURANCE": {"approve", "reject", "needs_input", "blocked"},
    "IMPLEMENTATION": {"complete", "in_progress", "needs_triage", "needs_input", "blocked"},
    "CHANGE_ASSURANCE": {"pass", "fail", "needs_triage", "needs_input", "blocked"},
    "DELIVERY": {"published", "needs_input", "blocked"},
    "AWAITING_INPUT": {"resolved", "needs_input", "blocked"},
    "COMPLETED": {"complete", "reopened"},
    "CANCELLED": {"cancelled"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--task-root", required=True, type=Path)
    value.add_argument("--lifecycle", required=True)
    value.add_argument("--outcome", required=True)
    value.add_argument("--reason", required=True)
    value.add_argument("--preview", action="store_true", help="Validate and show the proposed checkpoint without writing files")
    value.add_argument("--input-dir", type=Path, help="Prepared current documents, published with the checkpoint")
    value.add_argument("--expected-sequence", type=int)
    value.add_argument("--result-id", help="Stable identity for safe retries")
    value.add_argument("--next-lifecycle")
    value.add_argument("--route-reason")
    value.add_argument("--run-id")
    value.add_argument("--progress", choices=["yes", "no"])
    value.add_argument("--assignment-id")
    value.add_argument("--attempt", type=int)
    value.add_argument("--worker-tier", choices=["fast", "standard", "high"])
    value.add_argument("--worker-id")
    value.add_argument("--active-seconds", type=float)
    value.add_argument("--finding", action="append", default=[], type=json.loads)
    value.add_argument("--decision", action="append", default=[])
    return value


def submit(args) -> int:
    try:
        args.outcome = args.outcome.replace("-", "_").casefold()
        allowed = OUTCOMES.get(args.lifecycle)
        if allowed is None:
            raise ValueError(f"unknown lifecycle: {args.lifecycle}")
        if args.outcome not in allowed:
            raise ValueError(f"{args.lifecycle} outcome must be one of: {', '.join(sorted(allowed))}")
        if args.result_id is not None and not args.result_id.strip():
            raise ValueError("result-id must be nonempty when supplied")
        if args.expected_sequence is not None and args.expected_sequence < 0:
            raise ValueError("expected-sequence must not be negative")
        if not args.reason.strip():
            raise ValueError("reason must be nonempty text")
        if args.attempt is not None and args.attempt < 1:
            raise ValueError("attempt must be a positive integer")
        if args.active_seconds is not None and (not math.isfinite(args.active_seconds) or args.active_seconds < 0):
            raise ValueError("active-seconds must be finite and nonnegative when supplied")
        for finding in args.finding:
            if not isinstance(finding, dict) or finding.get("kind") not in {"missed_defect", "new_requirement", "dependency_change", "accepted_risk"}:
                raise ValueError("finding requires a supported kind")
            if any(not isinstance(finding.get(field), str) or not finding[field].strip() for field in ("summary", "revision", "evidence")):
                raise ValueError("finding requires summary, revision, and evidence")
        task_root = args.task_root.expanduser().resolve()
        source = args.input_dir.expanduser().resolve() if args.input_dir else task_root
        task_path = source / "task.json"
        report_path = source / "report.md"
        assurance_path = source / "assurance.json"
        history_path = task_root / "history.jsonl"

        history, history_errors = load_history(history_path)
        if history_errors:
            raise ValueError("; ".join(history_errors))
        if args.result_id:
            existing = next((item for item in history if item.get("result_id") == args.result_id), None)
            if existing:
                if existing["lifecycle"] != args.lifecycle or existing["outcome"] != args.outcome:
                    raise ValueError("Result identity was already used for a different lifecycle or outcome")
                if not args.preview and (task_root / "assignment.json").exists():
                    active = load_json(task_root / "assignment.json")
                    if active.get("assignment_id") == existing.get("assignment_id"):
                        finish_assignment(task_root, existing)
                print(json.dumps({"checkpoint": existing["sequence"], "next_lifecycle": existing["next_lifecycle"],
                                  "stop": existing["stop"], "reason": existing["route_reason"], "replayed": True}))
                return 0
        if args.expected_sequence is not None and args.expected_sequence != len(history):
            raise ValueError("The expected checkpoint sequence is stale")
        task = load_json(task_path)
        errors = validate_task(task)
        if not report_path.exists() or not report_path.read_text(encoding="utf-8").strip():
            errors.append("report.md must contain current human-readable text")
        assurance = load_json(assurance_path) if assurance_path.exists() else None
        if assurance is not None:
            errors.extend(validate_assurance(assurance, int(task["task_revision"])))
        if errors:
            raise ValueError("; ".join(errors))
        assignment = assignment_result(task_root, args.lifecycle, args.worker_id)
        if assignment:
            if assignment["task_revision"] != task["task_revision"] or assignment["sequence"] != len(history):
                raise ValueError("The active assignment belongs to an obsolete contract or checkpoint")
            args.worker_id = assignment["worker_id"]
            args.assignment_id = assignment["assignment_id"]
            args.run_id = assignment["run_id"]
            args.active_seconds = assignment["active_seconds"]
        if (not assignment and not args.run_id and history
                and task["continuation_mode"] == "automatic" and not history[-1].get("stop")):
            args.run_id = history[-1].get("run_id")
        if args.lifecycle in {"IMPLEMENTATION", "CHANGE_ASSURANCE", "PLAN_ASSURANCE"} and (not args.worker_id or not args.worker_id.strip()):
            raise ValueError("Implementation and review results require a worker identity")
        if task["continuation_mode"] == "automatic" and args.lifecycle not in {"COMPLETED", "AWAITING_INPUT", "CANCELLED"}:
            if not args.run_id or args.active_seconds is None or args.progress is None:
                raise ValueError("Automatic results require a run identity, measured duration, and progress outcome")
        contract_fields = ("task_revision", "objective", "acceptance_criteria", "scope", "authority", "deliverable")
        contract = {field: task.get(field) for field in contract_fields}
        contract_path = task_root / "contracts" / (str(task["task_revision"]) + ".json")
        if contract_path.exists() and load_json(contract_path) != contract:
            raise ValueError("Accepted behavior, scope, authority, or delivery changed without a new task revision")
        repository = Path(task["repository"])
        git_head, git_branch, worktree_dirty = git_facts(repository)
        git_base = git_base_revision(repository, task.get("base_ref"))
        if args.outcome == "reopened" and history and history[-1].get("report_sha256") == digest(report_path):
            raise ValueError("Update the current report before reopening work")
        completed = [index for index, entry in enumerate(history) if entry.get("lifecycle") == "COMPLETED" and entry.get("status") == "terminal"]
        if completed and args.lifecycle not in {"COMPLETED", "CANCELLED"} and not any(
            entry.get("outcome") == "reopened" and entry.get("next_lifecycle") in {"TRIAGE", "IMPLEMENTATION"}
            for entry in history[completed[-1] + 1:]
        ):
            raise ValueError("Reopen the completed task before checkpointing further work")
        decision = decide(
            task,
            assurance,
            history,
            args.lifecycle,
            args.outcome,
            proposed_next=args.next_lifecycle, route_reason=args.route_reason,
            worker_id=args.worker_id, run_id=args.run_id, active_seconds=args.active_seconds,
            progress=None if args.progress is None else args.progress == "yes",
            files=changed_files(repository, git_base, git_head) if git_head and git_base else None,
            git_head=git_head,
            git_base=git_base,
            git_branch=git_branch,
            worktree_dirty=worktree_dirty,
        )
        status = "terminal" if args.lifecycle in {"COMPLETED", "CANCELLED"} and decision.next_lifecycle is None else (
            "awaiting_input" if decision.next_lifecycle == "AWAITING_INPUT" else "checkpointed"
        )
        record = {
            "schema_version": 1,
            "sequence": len(history) + 1,
            "result_id": args.result_id,
            "proposed_next": args.next_lifecycle,
            "proposed_reason": args.route_reason,
            "run_id": args.run_id,
            "progress": None if args.progress is None else args.progress == "yes",
            "plan_fingerprint": plan_fingerprint(assurance or {}),
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
            "worker_id": args.worker_id,
            "active_seconds": args.active_seconds,
            "findings": args.finding,
            "decisions": args.decision,
            "git_base": git_base,
            "git_head": git_head,
            "git_branch": git_branch,
            "worktree_dirty": worktree_dirty,
            "task_sha256": digest(task_path),
            "assurance_sha256": digest(assurance_path) if assurance_path.exists() else None,
            "report_sha256": digest(report_path),
        }
        if status == "terminal" and args.lifecycle == "COMPLETED":
            record["delivery"] = {
                "summary": args.reason.strip(),
                "evidence": [{key: item.get(key) for key in ("id", "proof", "result")} for item in assurance["evidence"]],
                "exceptions": assurance["exceptions"],
            }
        if args.preview:
            print(json.dumps({"preview": True, "record": record}, ensure_ascii=False, separators=(",", ":")))
            return 0
        if task["status"] == "aligned":
            contract_path.parent.mkdir(exist_ok=True)
            if not contract_path.exists():
                replace_text(contract_path, json.dumps(contract, sort_keys=True))
        publish(task_root, source, record)
        finish_assignment(task_root, record)
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


def main() -> int:
    args = parser().parse_args()
    if args.preview:
        if (args.task_root.expanduser().resolve() / "pending-checkpoint.json").exists():
            print("Factory checkpoint failed: recover the pending checkpoint first", file=sys.stderr)
            return 1
        return submit(args)
    try:
        root = args.task_root.expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        with (root / ".checkpoint.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            recovered = recover(root)
            if recovered:
                finish_assignment(root, recovered)
            return submit(args)
    except (OSError, ValueError) as error:
        print(f"Factory checkpoint failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
