#!/usr/bin/env python3
"""Append one sanitized Factory telemetry event to events.jsonl."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from telemetry_schema import CATEGORIES, EVENT_TYPES, FAILURE_CLASSES, normalize_timestamp, sanitize, utc_now

def resolve_task_root(explicit_root: str | None) -> Path:
    if explicit_root:
        return Path(explicit_root).expanduser().resolve()

    resolver = Path(__file__).resolve().parents[2] / "factory-handoff" / "scripts" / "resolve-handoff-path.sh"
    result = subprocess.run(
        [str(resolver), "--root"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-root")
    parser.add_argument("--event-type", required=True, choices=sorted(EVENT_TYPES))
    parser.add_argument("--summary", required=True)
    parser.add_argument("--occurred-at")
    parser.add_argument("--run-id")
    parser.add_argument("--resumes-run-id")
    parser.add_argument("--task-revision", type=int)
    parser.add_argument("--lifecycle")
    parser.add_argument("--assignment-id")
    parser.add_argument("--invocation-id")
    parser.add_argument("--worker-profile")
    parser.add_argument("--operation-id")
    parser.add_argument("--attempt", type=int)
    parser.add_argument("--retry-of")
    parser.add_argument("--retry-reason")
    parser.add_argument("--precondition-change")
    parser.add_argument("--category", choices=sorted(CATEGORIES))
    parser.add_argument("--status")
    parser.add_argument("--failure-class", choices=sorted(FAILURE_CLASSES))
    parser.add_argument("--duration-ms", type=int)
    parser.add_argument("--corrects-event-id")
    parser.add_argument("--git-head")
    parser.add_argument("--diff-fingerprint")
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--best-effort", action="store_true")
    return parser


def build_event(args: argparse.Namespace) -> dict[str, object]:
    recorded_at = utc_now()
    event: dict[str, object] = {
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "event_type": args.event_type,
        "occurred_at": normalize_timestamp(args.occurred_at) if args.occurred_at else recorded_at,
        "recorded_at": recorded_at,
        "summary": sanitize(args.summary),
    }
    optional_values = {
        "run_id": args.run_id,
        "resumes_run_id": args.resumes_run_id,
        "task_revision": args.task_revision,
        "lifecycle": args.lifecycle,
        "assignment_id": args.assignment_id,
        "invocation_id": args.invocation_id,
        "worker_profile": args.worker_profile,
        "operation_id": args.operation_id,
        "attempt": args.attempt,
        "retry_of": args.retry_of,
        "retry_reason": args.retry_reason,
        "precondition_change": args.precondition_change,
        "category": args.category,
        "status": args.status,
        "failure_class": args.failure_class,
        "duration_ms": args.duration_ms,
        "corrects_event_id": args.corrects_event_id,
        "git_head": args.git_head,
        "diff_fingerprint": args.diff_fingerprint,
    }
    for key, value in optional_values.items():
        if value is not None:
            event[key] = sanitize(value) if isinstance(value, str) else value
    if args.evidence:
        event["evidence"] = [sanitize(item) for item in args.evidence]
    if args.changed_file:
        event["changed_files"] = [sanitize(item) for item in args.changed_file]
    if args.artifact:
        event["artifacts"] = [sanitize(item) for item in args.artifact]
    if args.attempt is not None and args.attempt < 1:
        raise ValueError("attempt must be a positive integer")
    retry_start_events = {
        "operation_started", "recovery_started", "wait_started",
        "external_action_attempted",
    }
    if args.event_type in retry_start_events and args.attempt is not None and args.attempt > 1:
        if not args.retry_of:
            raise ValueError("a retry must name retry-of")
        if not args.retry_reason and not args.precondition_change:
            raise ValueError("a retry must name retry-reason or precondition-change")
    if args.duration_ms is not None and args.duration_ms < 0:
        raise ValueError("duration-ms must not be negative")
    return event


def append_event(task_root: Path, event: dict[str, object]) -> Path:
    telemetry_root = task_root / "telemetry"
    telemetry_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    (telemetry_root / "artifacts").mkdir(exist_ok=True, mode=0o700)
    events_path = telemetry_root / "events.jsonl"
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"

    descriptor = os.open(events_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        with os.fdopen(descriptor, "a", encoding="utf-8", closefd=True) as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    except Exception:
        raise
    return events_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        event = build_event(args)
        path = append_event(resolve_task_root(args.task_root), event)
        print(f"Recorded telemetry event {event['event_id']} in {path}")
        return 0
    except Exception as error:
        print(f"Telemetry event was not recorded: {error}", file=sys.stderr)
        return 0 if args.best_effort else 1


if __name__ == "__main__":
    raise SystemExit(main())
