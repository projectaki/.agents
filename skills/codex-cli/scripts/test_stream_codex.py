#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("stream_codex.py")


def fake_codex(directory: Path, body: str) -> Path:
    executable = directory / "fake-codex"
    executable.write_text("#!/usr/bin/env python3\n" + textwrap.dedent(body), encoding="utf-8")
    executable.chmod(0o700)
    return executable


def run_wrapper(fake: Path, *extra: str) -> tuple[subprocess.CompletedProcess[str], list[dict]]:
    completed = subprocess.run(
        [
            "python3", str(SCRIPT),
            "--repository", str(SCRIPT.parent),
            "--model", "fixture-model",
            "--reasoning-effort", "high",
            "--sandbox", "read-only",
            "--codex-bin", str(fake),
            *extra,
        ],
        input="Review this fixture",
        text=True,
        capture_output=True,
        timeout=10,
    )
    events = [json.loads(line) for line in completed.stdout.splitlines()]
    return completed, events


class StreamCodexTests(unittest.TestCase):
    def test_streams_safe_progress_and_final_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = fake_codex(Path(tmp), r'''
                import json
                events = [
                    {"type": "thread.started", "thread_id": "secret-session"},
                    {"type": "turn.started"},
                    {"type": "item.started", "item": {"type": "command_execution", "command": "cat token.txt"}},
                    {"type": "item.completed", "item": {"type": "reasoning", "text": "private reasoning"}},
                    {"type": "item.completed", "item": {"type": "command_execution", "aggregated_output": "token=do-not-leak"}},
                    {"type": "item.completed", "item": {"type": "agent_message", "text": "Review complete."}},
                    {"type": "turn.completed", "usage": {"input_tokens": 10}},
                ]
                for event in events:
                    print(json.dumps(event), flush=True)
            ''')
            completed, events = run_wrapper(fake)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(any(e["type"] == "tool" and e["name"] == "command_execution" for e in events))
        self.assertEqual(next(e["response"] for e in events if e["type"] == "result"), "Review complete.")
        rendered = json.dumps(events)
        self.assertNotIn("private reasoning", rendered)
        self.assertNotIn("do-not-leak", rendered)
        self.assertNotIn("secret-session", rendered)

    def test_result_only_emits_only_final_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = fake_codex(Path(tmp), r'''
                import json
                events = [
                    {"type": "turn.started"},
                    {"type": "item.started", "item": {"type": "command_execution", "command": "rg TODO"}},
                    {"type": "item.completed", "item": {"type": "agent_message", "text": "Candidate plan."}},
                    {"type": "turn.completed"},
                ]
                for event in events:
                    print(json.dumps(event), flush=True)
            ''')
            completed, events = run_wrapper(fake, "--delivery", "result-only")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            events,
            [{"type": "result", "status": "completed", "response": "Candidate plan."}],
        )

    def test_stops_after_no_codex_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = fake_codex(Path(tmp), r'''
                import time
                time.sleep(5)
            ''')
            completed, events = run_wrapper(fake, "--stall-seconds", "1", "--heartbeat-seconds", "1")

        self.assertEqual(completed.returncode, 124)
        self.assertTrue(any(e["type"] == "error" and "stalled" in e["message"] for e in events))

    def test_nonzero_exit_does_not_leak_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = fake_codex(Path(tmp), r'''
                import sys
                print("token=do-not-leak", file=sys.stderr, flush=True)
                raise SystemExit(7)
            ''')
            completed, events = run_wrapper(fake)

        self.assertEqual(completed.returncode, 7)
        rendered = json.dumps(events)
        self.assertNotIn("do-not-leak", rendered)
        self.assertIn("Codex exited with code 7", rendered)


if __name__ == "__main__":
    unittest.main()
