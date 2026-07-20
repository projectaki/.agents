#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("init_video_evidence_run.py")


class InitVideoEvidenceRunTest(unittest.TestCase):
    def test_creates_unique_runs_under_current_users_home(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_home:
            environment = os.environ.copy()
            environment["HOME"] = temporary_home
            environment["TMPDIR"] = str(Path(temporary_home) / "temporary")

            first_run = self.run_initializer(environment)
            second_run = self.run_initializer(environment)

            expected_thread_root = (
                Path(temporary_home) / "evidence" / "my-project" / "fix-login-flow"
            )
            self.assertEqual(first_run.parent, expected_thread_root)
            self.assertEqual(second_run.parent, expected_thread_root)
            self.assertNotEqual(first_run, second_run)
            self.assertRegex(first_run.name, r"^\d{8}T\d{12}Z$")

            for run in (first_run, second_run):
                self.assertEqual(
                    sorted(path.name for path in run.iterdir()),
                    ["publish", "workflows"],
                )
                self.assertEqual(list((run / "publish").iterdir()), [])

    def run_initializer(self, environment: dict[str, str]) -> Path:
        result = subprocess.run(
            [
                str(SCRIPT),
                "--project",
                "My Project",
                "--thread",
                "Fix Login Flow",
            ],
            check=True,
            capture_output=True,
            env=environment,
            text=True,
        )
        return Path(result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
