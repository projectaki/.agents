#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).parent
WRITER = SCRIPTS / "record-event.py"
SUMMARIZER = SCRIPTS / "summarize-events.py"


class RuntimeScenarioTests(unittest.TestCase):
    def record(self, root: Path, event_type: str, occurred_at: str, summary: str, *arguments: str) -> None:
        result = subprocess.run(
            [
                "python3", str(WRITER), "--task-root", str(root),
                "--event-type", event_type, "--occurred-at", occurred_at,
                "--summary", summary, *arguments,
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_multi_day_docker_failure_recovery_and_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.record(root, "run_started", "2026-08-28T14:00:00Z", "Implementation run started", "--run-id", "run-1", "--lifecycle", "IMPLEMENTATION")
            self.record(root, "operation_started", "2026-08-28T14:01:00Z", "Start Docker", "--run-id", "run-1", "--operation-id", "docker-start", "--attempt", "1", "--category", "environment_setup")
            self.record(root, "operation_failed", "2026-08-28T14:11:00Z", "Docker did not become healthy", "--run-id", "run-1", "--operation-id", "docker-start", "--attempt", "1", "--category", "environment_setup", "--failure-class", "environment")
            self.record(root, "operation_started", "2026-08-28T14:12:00Z", "Retry unchanged Docker startup after a transient timeout", "--run-id", "run-1", "--operation-id", "docker-start", "--attempt", "2", "--retry-of", "docker-attempt-1", "--retry-reason", "The timeout can be transient.", "--category", "environment_setup")
            self.record(root, "operation_failed", "2026-08-28T14:22:00Z", "Docker did not become healthy", "--run-id", "run-1", "--operation-id", "docker-start", "--attempt", "2", "--category", "environment_setup", "--failure-class", "environment")
            self.record(root, "recovery_started", "2026-08-28T14:23:00Z", "Remove the stale container", "--run-id", "run-1", "--operation-id", "docker-recovery", "--attempt", "1", "--category", "recovery")
            self.record(root, "recovery_finished", "2026-08-28T14:28:00Z", "Removed the stale container", "--run-id", "run-1", "--operation-id", "docker-recovery", "--attempt", "1", "--category", "recovery")
            self.record(root, "operation_started", "2026-08-28T14:29:00Z", "Start Docker after recovery", "--run-id", "run-1", "--operation-id", "docker-start", "--attempt", "3", "--retry-of", "docker-attempt-2", "--precondition-change", "Removed the stale container.", "--category", "environment_setup")
            self.record(root, "operation_succeeded", "2026-08-28T14:32:00Z", "Docker became healthy", "--run-id", "run-1", "--operation-id", "docker-start", "--attempt", "3", "--category", "environment_setup")
            self.record(root, "operation_started", "2026-08-28T14:40:00Z", "Run integration tests", "--run-id", "run-1", "--operation-id", "integration-tests", "--attempt", "1", "--category", "assurance")
            self.record(root, "run_interrupted", "2026-08-28T15:00:00Z", "The run stopped before the tests returned", "--run-id", "run-1", "--lifecycle", "IMPLEMENTATION")
            self.record(root, "run_resumed", "2026-08-29T09:00:00Z", "Change assurance resumed", "--run-id", "run-2", "--resumes-run-id", "run-1", "--lifecycle", "CHANGE_ASSURANCE")
            self.record(root, "operation_started", "2026-08-29T09:05:00Z", "Run final assurance", "--run-id", "run-2", "--operation-id", "final-assurance", "--attempt", "1", "--category", "assurance")
            self.record(root, "operation_succeeded", "2026-08-29T09:35:00Z", "Final assurance passed", "--run-id", "run-2", "--operation-id", "final-assurance", "--attempt", "1", "--category", "assurance")
            self.record(root, "run_finished", "2026-08-29T10:00:00Z", "Change assurance run finished", "--run-id", "run-2", "--lifecycle", "CHANGE_ASSURANCE")

            subprocess.run(["python3", str(SUMMARIZER), "--task-root", str(root), "--strict"], check=True)
            summary = (root / "telemetry" / "summary.md").read_text(encoding="utf-8")
            self.assertIn("Completed-run active time | 1h 0m 0s", summary)
            self.assertIn("Incomplete-run lower bound | 1h 0m 0s", summary)
            self.assertIn("Pause or unobserved gap | 18h 0m 0s", summary)
            self.assertIn("Failed operations: 2", summary)
            self.assertIn("Retries: 2", summary)
            self.assertIn("Operations without a result: 1", summary)
            self.assertIn("environment_setup | 23m 0s", summary)
            self.assertIn("recovery | 5m 0s", summary)

            canonical_state = root / "task.json"
            canonical_state.write_text("canonical state", encoding="utf-8")
            bad_root = root / "not-a-directory"
            bad_root.write_text("occupied", encoding="utf-8")
            result = subprocess.run(
                [
                    "python3", str(WRITER), "--task-root", str(bad_root),
                    "--event-type", "run_started", "--summary", "Logging fails",
                    "--best-effort",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode)
            self.assertEqual("canonical state", canonical_state.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
