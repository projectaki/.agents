#!/usr/bin/env python3
"""Fixture tests for the observable Claude wrapper."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("stream_claude.py")


def fake_claude(directory: Path, body: str) -> Path:
    executable = directory / "fake-claude"
    executable.write_text("#!/usr/bin/env python3\n" + textwrap.dedent(body), encoding="utf-8")
    executable.chmod(0o700)
    return executable


def run_wrapper(fake: Path, *extra: str) -> tuple[subprocess.CompletedProcess[str], list[dict]]:
    completed = subprocess.run(
        [
            "python3", str(SCRIPT),
            "--repository", str(SCRIPT.parent),
            "--model", "fixture-model",
            "--effort", "high",
            "--permission-mode", "plan",
            "--tools", "Read,Grep,Glob,Bash",
            "--claude-bin", str(fake),
            *extra,
        ],
        input="Review this fixture",
        text=True,
        capture_output=True,
        timeout=10,
    )
    events = [json.loads(line) for line in completed.stdout.splitlines()]
    return completed, events


class StreamClaudeTests(unittest.TestCase):
    def test_streams_safe_progress_and_final_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = fake_claude(Path(tmp), r'''
                import json
                events = [
                    {"type": "system", "subtype": "init"},
                    {"type": "stream_event", "event": {"type": "content_block_start", "content_block": {"type": "tool_use", "name": "Read", "input": {"file_path": "/repo/app.ts", "pattern": "SECRET"}}}},
                    {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "thinking_delta", "thinking": "private reasoning"}}},
                    {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Ready with "}}},
                    {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "changes."}}},
                    {"type": "user", "tool_use_result": "sensitive tool output"},
                    {"type": "result", "subtype": "success", "result": "Ready with changes."},
                ]
                for event in events:
                    print(json.dumps(event), flush=True)
            ''')
            completed, events = run_wrapper(fake)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(any(e["type"] == "tool" and e["name"] == "Read" for e in events))
        self.assertEqual("".join(e["text"] for e in events if e["type"] == "text"), "Ready with changes.")
        self.assertEqual(next(e["response"] for e in events if e["type"] == "result"), "Ready with changes.")
        rendered = json.dumps(events)
        self.assertNotIn("private reasoning", rendered)
        self.assertNotIn("sensitive tool output", rendered)
        self.assertNotIn("SECRET", rendered)

    def test_stops_after_no_claude_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = fake_claude(Path(tmp), r'''
                import time
                time.sleep(5)
            ''')
            completed, events = run_wrapper(fake, "--stall-seconds", "1", "--heartbeat-seconds", "1")

        self.assertEqual(completed.returncode, 124)
        self.assertTrue(any(e["type"] == "error" and "stalled" in e["message"] for e in events))

    def test_nonzero_exit_does_not_leak_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = fake_claude(Path(tmp), r'''
                import sys
                print("token=do-not-leak", file=sys.stderr, flush=True)
                raise SystemExit(7)
            ''')
            completed, events = run_wrapper(fake)

        self.assertEqual(completed.returncode, 7)
        rendered = json.dumps(events)
        self.assertNotIn("do-not-leak", rendered)
        self.assertIn("Claude exited with code 7", rendered)


if __name__ == "__main__":
    unittest.main()
