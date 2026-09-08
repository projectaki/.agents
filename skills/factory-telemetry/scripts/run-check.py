#!/usr/bin/env python3
"""Run a focused check with timing, a timeout, and a compact execution receipt."""

from __future__ import annotations

import argparse
import json
import math
import os
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "factory-handoff/scripts"))
from records import git_base_revision, git_facts, load_json
from runtime import emit
from telemetry_schema import sanitize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-root", required=True, type=Path)
    parser.add_argument("--cwd", required=True, type=Path)
    parser.add_argument("--proof", required=True, help="Safe test target description; exclude credentials and private URLs")
    parser.add_argument("--environment", required=True, help="Safe environment description needed to assess reuse")
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("Supply a command and a finite timeout greater than zero")
    root = args.task_root.expanduser().resolve()
    task = load_json(root / "task.json")
    assignment_path = root / "assignment.json"
    assignment = load_json(assignment_path) if assignment_path.exists() else {}
    timeout = args.timeout
    if assignment.get("timeout_seconds") is not None:
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(assignment["started_at"])).total_seconds()
        timeout = min(timeout, max(0, assignment["timeout_seconds"] - elapsed))
    operation = str(uuid.uuid4())
    fields = dict(operation_id=operation, run_id=assignment.get("run_id"), category="assurance")
    head, branch, dirty = git_facts(args.cwd)
    base = git_base_revision(args.cwd, task.get("base_ref"))
    emit(root, "operation_started", **fields)
    started = time.monotonic()
    process = None
    try:
        if timeout <= 0:
            raise subprocess.TimeoutExpired(command, timeout)
        process = subprocess.Popen(command, cwd=args.cwd, start_new_session=True)
        result = process.wait(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        result = 124
    except OSError:
        result = 127
    duration = int((time.monotonic() - started) * 1000)
    emit(root, "operation_succeeded" if result == 0 else "operation_failed",
         duration_ms=duration, failure_class=None if result == 0 else "timeout" if result == 124 else "product", **fields)
    final_head, final_branch, final_dirty = git_facts(args.cwd)
    receipt = dict(id=operation, proof=sanitize(args.proof), working_directory=str(args.cwd.resolve()),
                   environment=sanitize(args.environment), revision=head, base_revision=base,
                   branch=branch, started_dirty=dirty, finished_dirty=final_dirty,
                   revision_unchanged=(head, branch) == (final_head, final_branch),
                   exit_status=result, duration_ms=duration, state="executed",
                   result="pass" if result == 0 else "fail")
    try:
        directory = root / "artifacts/checks"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (operation + ".json")
        path.write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"Factory check receipt: {path}")
    except OSError:
        print("Factory check receipt could not be saved; preserve the observed result before review.", file=sys.stderr)
    return result if result >= 0 else 128 - result


if __name__ == "__main__":
    raise SystemExit(main())
