#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("summarize-events.py")


def event(event_id: str, event_type: str, occurred_at: str, **values: object) -> dict[str, object]:
    return {
        "schema_version": 1,
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "recorded_at": occurred_at,
        "summary": event_type,
        **values,
    }


class SummarizeEventsTests(unittest.TestCase):
    def write_events(self, root: Path, events: list[dict[str, object]], extra: str = "") -> None:
        telemetry = root / "telemetry"
        telemetry.mkdir(parents=True)
        content = "\n".join(json.dumps(item) for item in events) + "\n" + extra
        (telemetry / "events.jsonl").write_text(content, encoding="utf-8")

    def test_excludes_next_day_pause_from_active_time(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_events(root, [
                event("1", "run_started", "2026-08-28T14:00:00Z", run_id="run-1"),
                event("2", "run_interrupted", "2026-08-28T15:00:00Z", run_id="run-1"),
                event("3", "run_resumed", "2026-08-29T09:00:00Z", run_id="run-2", resumes_run_id="run-1"),
                event("4", "run_finished", "2026-08-29T10:00:00Z", run_id="run-2"),
            ])
            result = subprocess.run(
                ["python3", str(SCRIPT), "--task-root", str(root)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            summary = (root / "telemetry" / "summary.md").read_text(encoding="utf-8")
            self.assertIn("Completed-run active time | 1h 0m 0s", summary)
            self.assertIn("Incomplete-run lower bound | 1h 0m 0s", summary)
            self.assertIn("Pause or unobserved gap | 18h 0m 0s", summary)

    def test_groups_retries_failures_and_category_time(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_events(root, [
                event("0", "run_started", "2026-08-28T06:59:00Z", run_id="run-1"),
                event("1", "operation_started", "2026-08-28T07:00:00Z", run_id="run-1", operation_id="docker", attempt=1, category="environment_setup"),
                event("2", "operation_failed", "2026-08-28T07:10:00Z", run_id="run-1", operation_id="docker", attempt=1, category="environment_setup"),
                event("3", "operation_started", "2026-08-28T07:12:00Z", run_id="run-1", operation_id="docker", attempt=2, retry_of="2", retry_reason="The failure was transient.", category="environment_setup"),
                event("4", "operation_succeeded", "2026-08-28T07:20:00Z", run_id="run-1", operation_id="docker", attempt=2, category="environment_setup"),
                event("5", "run_finished", "2026-08-28T07:21:00Z", run_id="run-1"),
            ])
            subprocess.run(["python3", str(SCRIPT), "--task-root", str(root)], check=True)
            summary = (root / "telemetry" / "summary.md").read_text(encoding="utf-8")
            self.assertIn("Failed operations: 1", summary)
            self.assertIn("Retries: 1", summary)
            self.assertIn("environment_setup | 18m 0s", summary)

    def test_strict_mode_reports_malformed_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_events(root, [event("1", "run_started", "2026-08-28T07:00:00Z")], "{")
            result = subprocess.run(
                ["python3", str(SCRIPT), "--task-root", str(root), "--strict"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(1, result.returncode)
            self.assertIn("Line 2", result.stderr)

    def test_reports_duplicate_run_and_actor_terminal_events(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_events(root, [
                event("1", "run_started", "2026-08-28T07:00:00Z", run_id="run-1"),
                event("2", "actor_dispatched", "2026-08-28T07:01:00Z", run_id="run-1", invocation_id="actor-1"),
                event("3", "actor_completed", "2026-08-28T07:02:00Z", run_id="run-1", invocation_id="actor-1"),
                event("4", "actor_completed", "2026-08-28T07:03:00Z", run_id="run-1", invocation_id="actor-1"),
                event("5", "run_finished", "2026-08-28T07:04:00Z", run_id="run-1"),
                event("6", "run_finished", "2026-08-28T07:05:00Z", run_id="run-1"),
            ])
            result = subprocess.run(
                ["python3", str(SCRIPT), "--task-root", str(root), "--strict"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(1, result.returncode)
            self.assertIn("Actor actor-1 has 2 terminal events", result.stderr)
            self.assertIn("Run run-1 has 2 terminal events", result.stderr)

    def test_reports_invalid_retry_and_recovery_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_events(root, [
                event("1", "operation_started", "2026-08-28T07:00:00Z", run_id="run-1", operation_id="build", attempt=2, retry_of="attempt-1", retry_reason="Transient"),
                event("2", "operation_succeeded", "2026-08-28T07:01:00Z", run_id="run-1", operation_id="build", attempt=2),
                event("3", "recovery_started", "2026-08-28T07:02:00Z", run_id="run-2", operation_id="recovery", attempt=1),
                event("4", "recovery_finished", "2026-08-28T07:03:00Z", run_id="run-2", operation_id="recovery", attempt=1),
            ])
            result = subprocess.run(
                ["python3", str(SCRIPT), "--task-root", str(root), "--strict"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(1, result.returncode)
            self.assertIn("has no failed prior attempt", result.stderr)
            self.assertIn("starts before a failure", result.stderr)


if __name__ == "__main__":
    unittest.main()
