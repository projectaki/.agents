"""Assignment timing and best-effort event recording at Factory boundaries."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def emit(task_root, event_type, **fields):
    writer = Path(__file__).resolve().parents[2] / "factory-telemetry/scripts/record-event.py"
    command = [sys.executable, str(writer), "--task-root", str(task_root),
               "--event-type", event_type, "--summary", event_type.replace("_", " ")]
    for key, value in fields.items():
        if value is not None:
            command.extend(["--" + key.replace("_", "-"), str(value)])
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
        if result.returncode:
            raise OSError("event writer returned an error")
        return True
    except (OSError, subprocess.TimeoutExpired):
        print("Factory telemetry recording failed; product work can continue.", file=sys.stderr)
        try:
            (task_root / "telemetry-warning.txt").write_text("Telemetry is incomplete. A boundary event could not be recorded.\n")
        except OSError:
            pass
        return False


def assignment_result(task_root, lifecycle, worker_id):
    path = task_root / "assignment.json"
    if not path.exists():
        return None
    assignment = json.loads(path.read_text())
    if assignment["lifecycle"] != lifecycle or worker_id and assignment["worker_id"] != worker_id:
        raise ValueError("The result does not match the active assignment")
    started = datetime.fromisoformat(assignment["started_at"])
    assignment["active_seconds"] = max(0, (datetime.now(timezone.utc) - started).total_seconds())
    return assignment


def finish_assignment(task_root, record):
    assignment = task_root / "assignment.json"
    active = json.loads(assignment.read_text()) if assignment.exists() else {}
    if record.get("assignment_id") and active.get("assignment_id") == record["assignment_id"]:
        fields = dict(run_id=record["run_id"], assignment_id=record["assignment_id"],
                      invocation_id=record["assignment_id"], worker_id=record["worker_id"], lifecycle=record["lifecycle"])
        emit(task_root, "actor_completed", **fields)
        if record["stop"] or record["continuation_mode"] == "supervised":
            emit(task_root, "run_finished", run_id=record["run_id"])
        assignment.unlink()
    elif record.get("run_id") and record["stop"] and record["continuation_mode"] == "automatic":
        emit(task_root, "run_finished", run_id=record["run_id"])
    emit(task_root, "checkpoint_recorded", lifecycle=record["lifecycle"], task_revision=record["task_revision"])
