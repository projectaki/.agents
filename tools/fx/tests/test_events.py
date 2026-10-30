import concurrent.futures
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fx_events import capture_event, prepare_events, save_event
from fx_context import prepare_context, save_response


TOOL_DIRECTORY = Path(__file__).resolve().parents[1]


class EventsTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.task = Path(self.temporary.name)
        self.session = self.task / "context/session-test"
        self.session.mkdir(parents=True)

    def records(self):
        return [json.loads(line) for line in (self.session / "events/callbacks.jsonl").read_text().splitlines()]

    def test_records_preserve_payloads_and_duplicates_with_order_and_timestamps(self):
        payload = {"hook_event_name": "PreToolUse", "tool_input": {"command": "echo café\n"}, "unknown": [1, None]}
        raw = json.dumps(payload)
        first = save_event(self.session, "test", "hook", raw)
        second = save_event(self.session, "test", "hook", raw)
        records = self.records()
        self.assertEqual([record["payload"] for record in records], [payload, payload])
        self.assertEqual(first, 0)
        self.assertGreater(second, first)
        self.assertEqual([record["offset"] for record in records], [first, second])
        for record in records:
            self.assertEqual(record["schema_version"], 1)
            self.assertEqual(record["agent"], "test")
            self.assertEqual(record["source"], "hook")
            self.assertTrue(record["received_at"].endswith("+00:00"))
            self.assertGreater(record["monotonic_ns"], 0)
        events = self.session / "events"
        self.assertEqual(events.stat().st_mode & 0o777, 0o700)
        self.assertEqual((events / "callbacks.jsonl").stat().st_mode & 0o777, 0o600)

    def test_concurrent_processes_produce_complete_records_with_correct_offsets(self):
        script = TOOL_DIRECTORY / "agents/codex_capture.py"
        environment = dict(os.environ, FX_SESSION_CONTEXT_DIR=str(self.session))
        def send(number):
            return subprocess.run([sys.executable, script, "hook"], env=environment,
                                  input=json.dumps({"number": number, "text": "x" * 10000}),
                                  text=True, capture_output=True, check=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(send, range(12)))
        records = self.records()
        self.assertEqual(sorted(record["payload"]["number"] for record in records), list(range(12)))
        offset = 0
        for line in (self.session / "events/callbacks.jsonl").read_bytes().splitlines(keepends=True):
            self.assertEqual(json.loads(line)["offset"], offset)
            offset += len(line)

    def test_malformed_payload_is_kept_as_raw_text(self):
        save_event(self.session, "test", "hook", '{"broken": café')
        self.assertEqual(self.records()[0]["raw_payload"], '{"broken": café')

    def test_invalid_arguments_do_not_create_events(self):
        for agent, source, payload in (("", "hook", "{}"), ("test", None, "{}"), ("test", "hook", {})):
            with self.subTest(agent=agent, source=source):
                with self.assertRaises(ValueError):
                    save_event(self.session, agent, source, payload)
        self.assertFalse((self.session / "events").exists())

    def test_partial_writes_are_completed(self):
        original = os.write
        with patch("fx_events.os.write", side_effect=lambda fd, data: original(fd, data[:17])):
            save_event(self.session, "test", "hook", '{"text":"complete"}')
        self.assertEqual(self.records()[0]["payload"], {"text": "complete"})

    def test_failed_write_rolls_back_only_the_new_record(self):
        save_event(self.session, "test", "hook", "{}")
        path = self.session / "events/callbacks.jsonl"
        before = path.read_bytes()
        original = os.write
        def fail_after_partial_write(fd, data):
            original(fd, data[:17])
            raise OSError("disk full")
        with patch("fx_events.os.write", side_effect=fail_after_partial_write):
            with self.assertRaisesRegex(OSError, "disk full"):
                save_event(self.session, "test", "hook", "{}")
        self.assertEqual(path.read_bytes(), before)
        save_event(self.session, "test", "hook", "{}")
        self.assertEqual(len(self.records()), 2)

    def test_incomplete_tail_is_preserved_and_reported(self):
        path = prepare_events(self.session) / "callbacks.jsonl"
        path.write_text('{"incomplete":')
        with patch("sys.stderr"):
            capture_event(self.session, "test", "hook", "{}")
        self.assertEqual(path.read_text(), '{"incomplete":')
        self.assertIn("incomplete last record", (self.session / "events/capture-error.txt").read_text())
        self.assertFalse((self.session / "capture-error.txt").exists())

    def test_events_and_log_symlinks_are_rejected(self):
        events = self.session / "events"
        events.symlink_to(self.task)
        with self.assertRaises(ValueError):
            save_event(self.session, "test", "hook", "{}")
        events.unlink()
        prepare_events(self.session)
        outside = self.task / "outside.jsonl"
        outside.write_text("keep\n")
        (events / "callbacks.jsonl").symlink_to(outside)
        with self.assertRaises(OSError):
            save_event(self.session, "test", "hook", "{}")
        self.assertEqual(outside.read_text(), "keep\n")

    def test_preparation_reserves_native_log_and_refuses_reuse_or_paths(self):
        script = TOOL_DIRECTORY / "fx_events.py"
        result = subprocess.run([sys.executable, script, self.session, "native.log"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        path = self.session / "events/native.log"
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        path.write_text("keep")
        for filename in ("native.log", "../escape", ".", "..", ""):
            with self.subTest(filename=filename):
                result = subprocess.run([sys.executable, script, self.session, filename], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_text(), "keep")

    def test_diagnostics_are_excluded_from_context_and_handoffs(self):
        save_response(self.session, "test", "conversation", "turn", "Final response")
        save_event(self.session, "test", "hook", '{"diagnostic":"private event contents"}')
        for sources in ([], [self.session]):
            context = prepare_context(self.task, sources)
            self.assertNotIn("private event contents", context)
            self.assertNotIn("events/", context)
        with self.assertRaisesRegex(ValueError, "Diagnostic events"):
            prepare_context(self.task, [self.session / "events"])
        event_result = self.session / "events/result"
        event_result.mkdir()
        (event_result / "response.md").write_text("Do not supply this")
        (event_result / "metadata.json").write_text("{}")
        alias = self.session / "event-alias"
        alias.symlink_to(event_result)
        with self.assertRaisesRegex(ValueError, "Diagnostic events"):
            prepare_context(self.task, [alias])

    def test_codex_hook_configuration_uses_a_stable_command_and_no_trust_bypass(self):
        script = TOOL_DIRECTORY / "agents/codex_capture.py"
        result = subprocess.run([sys.executable, script, "hooks-config", self.session], capture_output=True, text=True, check=True)
        self.assertIn("hooks.PreToolUse=", result.stdout)
        self.assertIn("hooks.Interrupt=", result.stdout)
        self.assertIn("hooks.SessionEnd=", result.stdout)
        self.assertNotIn(str(self.session), result.stdout)
        self.assertNotIn("bypass", result.stdout)

    def test_claude_hooks_preserve_all_received_events_without_model_context_output(self):
        script = TOOL_DIRECTORY / "agents/claude_capture.py"
        result = subprocess.run([sys.executable, script, "settings", self.session], capture_output=True, text=True, check=True)
        hooks = json.loads(result.stdout)["hooks"]
        self.assertNotIn("WorktreeCreate", hooks)
        self.assertNotIn("WorktreeRemove", hooks)
        self.assertNotIn("FileChanged", hooks)
        self.assertIn("PostToolUseFailure", hooks)
        self.assertIn("StopFailure", hooks)
        self.assertIn("SessionEnd", hooks)
        for name in hooks:
            event = {"hook_event_name": name, "session_id": "thread", "agent_id": "child", "details": "retained"}
            command = shlex.split(hooks[name][0]["hooks"][0]["command"])
            result = subprocess.run(command,
                                    input=json.dumps(event), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
        self.assertEqual(len(self.records()), len(hooks))
        self.assertFalse((self.session / "results").exists())

    def test_malformed_passive_event_does_not_mark_response_capture_as_failed(self):
        script = TOOL_DIRECTORY / "agents/claude_capture.py"
        result = subprocess.run([sys.executable, script, "event", self.session],
                                input="invalid JSON", capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(self.records()[0]["raw_payload"], "invalid JSON")
        self.assertFalse((self.session / "capture-error.txt").exists())

    def test_events_in_separate_sessions_stay_separate(self):
        other = self.task / "context/session-other"
        other.mkdir()
        save_event(self.session, "test", "hook", '{"session":"first"}')
        save_event(other, "test", "hook", '{"session":"second"}')
        self.assertEqual(self.records()[0]["payload"]["session"], "first")
        record = json.loads((other / "events/callbacks.jsonl").read_text())
        self.assertEqual(record["payload"]["session"], "second")
        self.assertEqual(record["offset"], 0)

    def test_failed_event_capture_does_not_prevent_final_response_capture(self):
        prepare_events(self.session)
        (self.session / "events/callbacks.jsonl").write_text("incomplete")
        event = {"type": "agent-turn-complete", "thread-id": "thread", "turn-id": "turn", "last-assistant-message": "Final answer"}
        script = TOOL_DIRECTORY / "agents/codex_capture.py"
        result = subprocess.run([sys.executable, script, "capture", self.session, json.dumps(event)], capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual((self.session / "last_turn_results.md").read_text(), "Final answer")
        self.assertTrue((self.session / "events/capture-error.txt").exists())
        self.assertIn("Final answer", prepare_context(self.task, [self.session]))


if __name__ == "__main__":
    unittest.main()
