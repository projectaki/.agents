#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("init_video_evidence_run.py")


class InitVideoEvidenceRunTest(unittest.TestCase):
    def test_reuses_branch_workspace_and_preserves_project_auth(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_home:
            environment = os.environ.copy()
            environment["HOME"] = temporary_home
            environment["TMPDIR"] = str(Path(temporary_home) / "temporary")

            first_run = self.run_initializer(environment)
            project_root = Path(temporary_home) / "evidence" / "my-project"
            auth_root = project_root / "_auth"
            instructions = auth_root / "instructions.md"
            credentials = auth_root / "credentials.env"

            instructions.write_text("custom auth instructions\n", encoding="utf-8")
            second_run = self.run_initializer(environment)

            expected_run = project_root / "feature-login"
            self.assertEqual(first_run, expected_run)
            self.assertEqual(second_run, expected_run)
            self.assertEqual(instructions.read_text(), "custom auth instructions\n")
            self.assertTrue(credentials.is_file())
            self.assertTrue((auth_root / "states").is_dir())
            self.assertEqual(auth_root.stat().st_mode & 0o777, 0o700)
            self.assertEqual(credentials.stat().st_mode & 0o777, 0o600)

            self.assertEqual(
                sorted(path.name for path in first_run.iterdir()),
                ["publish", "workflows"],
            )
            self.assertEqual(list((first_run / "publish").iterdir()), [])

    def run_initializer(self, environment: dict[str, str]) -> Path:
        result = subprocess.run(
            [
                str(SCRIPT),
                "--project",
                "My Project",
                "--branch",
                "feature/login",
            ],
            check=True,
            capture_output=True,
            env=environment,
            text=True,
        )
        return Path(result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
