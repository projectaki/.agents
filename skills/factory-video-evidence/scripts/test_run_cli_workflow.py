#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


RUNNER = Path(__file__).with_name("run_cli_workflow.sh")


class RunCliWorkflowTest(unittest.TestCase):
    def test_check_run_closes_its_session(self) -> None:
        with self.workspace() as workspace:
            result = self.run_workflow(workspace)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                self.commands(workspace),
                ["open", "goto", "run-code", "close"],
            )

    def test_run_restores_auth_state_before_navigation(self) -> None:
        with self.workspace() as workspace:
            state = Path(workspace) / "_auth" / "states" / "reviewer.json"
            state.parent.mkdir(parents=True)
            state.write_text('{"cookies": [], "origins": []}\n', encoding="utf-8")

            result = self.run_workflow(workspace, state=state)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                self.commands(workspace),
                ["open", "state-load", "goto", "run-code", "close"],
            )

    def test_recording_stops_video_and_closes_its_session(self) -> None:
        with self.workspace() as workspace:
            video = Path(workspace) / "publish" / "ui-login.webm"
            result = self.run_workflow(workspace, video=video)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(video.is_file())
            self.assertEqual(
                self.commands(workspace),
                ["open", "goto", "video-start", "run-code", "video-stop", "close"],
            )

    def test_failure_removes_partial_video_and_closes_its_session(self) -> None:
        with self.workspace() as workspace:
            video = Path(workspace) / "publish" / "ui-login.webm"
            result = self.run_workflow(workspace, video=video, fail_workflow=True)

            self.assertEqual(result.returncode, 42)
            self.assertFalse(video.exists())
            self.assertEqual(
                self.commands(workspace),
                ["open", "goto", "video-start", "run-code", "video-stop", "close"],
            )

    def test_existing_video_is_never_overwritten(self) -> None:
        with self.workspace() as workspace:
            video = Path(workspace) / "publish" / "ui-login.webm"
            video.parent.mkdir()
            video.write_text("existing evidence", encoding="utf-8")

            result = self.run_workflow(workspace, video=video)

            self.assertEqual(result.returncode, 2)
            self.assertEqual(video.read_text(), "existing evidence")

    def workspace(self) -> tempfile.TemporaryDirectory[str]:
        return tempfile.TemporaryDirectory()

    def run_workflow(
        self,
        workspace_value: str,
        *,
        video: Path | None = None,
        state: Path | None = None,
        fail_workflow: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        workspace = Path(workspace_value)
        binary_directory = workspace / "bin"
        publish_directory = workspace / "publish"
        binary_directory.mkdir()
        publish_directory.mkdir(exist_ok=True)

        workflow = workspace / "workflow.js"
        workflow.write_text("async page => page.url()\n", encoding="utf-8")

        fake_cli = binary_directory / "playwright-cli"
        fake_cli.write_text(
            """#!/usr/bin/env bash
set -u
printf '%s\\n' "$2" >> "$FAKE_PLAYWRIGHT_LOG"
if [[ "$2" == "video-start" ]]; then
  : > "$3"
fi
if [[ "$2" == "run-code" && "${FAIL_WORKFLOW:-0}" == "1" ]]; then
  exit 42
fi
""",
            encoding="utf-8",
        )
        fake_cli.chmod(0o755)

        environment = os.environ.copy()
        environment["PATH"] = f"{binary_directory}:{environment['PATH']}"
        environment["FAKE_PLAYWRIGHT_LOG"] = str(workspace / "commands.log")
        environment["FAIL_WORKFLOW"] = "1" if fail_workflow else "0"

        command = [
            str(RUNNER),
            "--session",
            "ui-login-123",
            "--url",
            "https://example.test/login",
            "--script",
            str(workflow),
        ]
        if video is not None:
            command.extend(["--video", str(video)])
        if state is not None:
            command.extend(["--state", str(state)])

        return subprocess.run(
            command,
            capture_output=True,
            env=environment,
            text=True,
        )

    def commands(self, workspace_value: str) -> list[str]:
        return (Path(workspace_value) / "commands.log").read_text().splitlines()


if __name__ == "__main__":
    unittest.main()
