#!/usr/bin/env python3

from __future__ import annotations

import concurrent.futures
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("record-event.py")


class RecordEventTests(unittest.TestCase):
    def run_writer(self, task_root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), "--task-root", str(task_root), *arguments],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_records_compact_sanitized_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.run_writer(
                root,
                "--event-type", "operation_failed",
                "--summary", "token=secret-value failed",
                "--run-id", "run-1",
                "--operation-id", "docker-start",
                "--attempt", "1",
                "--failure-class", "environment",
            )
            self.assertEqual(0, result.returncode, result.stderr)
            lines = (root / "telemetry" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(1, len(lines))
            event = json.loads(lines[0])
            self.assertEqual("token=[REDACTED] failed", event["summary"])
            self.assertEqual("docker-start", event["operation_id"])

    def test_parallel_writers_do_not_corrupt_lines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def write(number: int) -> int:
                return self.run_writer(
                    root,
                    "--event-type", "operation_started",
                    "--summary", f"Operation {number}",
                    "--run-id", "run-1",
                    "--operation-id", f"operation-{number}",
                ).returncode

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(write, range(40)))

            self.assertEqual([0] * 40, results)
            lines = (root / "telemetry" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(40, len(lines))
            self.assertEqual(40, len({json.loads(line)["event_id"] for line in lines}))

    def test_best_effort_does_not_fail_caller(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "not-a-directory"
            root.write_text("occupied", encoding="utf-8")
            result = self.run_writer(
                root,
                "--event-type", "run_started",
                "--summary", "Run started",
                "--best-effort",
            )
            self.assertEqual(0, result.returncode)
            self.assertIn("was not recorded", result.stderr)

    def test_retry_requires_correlation_and_justification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.run_writer(
                root,
                "--event-type", "operation_started",
                "--summary", "Retry Docker startup",
                "--operation-id", "docker-start",
                "--attempt", "2",
            )
            self.assertEqual(1, result.returncode)
            self.assertIn("retry must name retry-of", result.stderr)


if __name__ == "__main__":
    unittest.main()
