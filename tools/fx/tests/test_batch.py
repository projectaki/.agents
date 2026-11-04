import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agents"))
import claude_batch
import codex_batch


class BatchCaptureTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.output = Path(temporary.name) / "output"

    def codex_events(self, *events):
        self.output.write_text("".join(json.dumps(event) + "\n" for event in events))
        return codex_batch.final_response(self.output)

    def test_codex_uses_last_main_agent_message_after_turn_completion(self):
        result = self.codex_events(
            {"type": "thread.started", "thread_id": "conversation"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "Working"}},
            {"type": "item.completed", "item": {"type": "command_execution", "text": "Not a response"}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "Final report"}},
            {"type": "turn.completed"},
        )
        self.assertEqual(result, ("conversation", "Final report"))

    def test_codex_rejects_failed_incomplete_and_invalid_output(self):
        for events in (
            [], [[]], [{"type": "turn.failed"}], [{"type": "error"}],
            [{"type": "turn.completed"}],
            [{"type": "thread.started", "thread_id": "conversation"},
             {"type": "item.completed", "item": {"type": "agent_message", "text": "Partial"}}],
        ):
            with self.subTest(events=events), self.assertRaises(ValueError):
                self.codex_events(*events)
        self.output.write_text('{"type":')
        with self.assertRaises(ValueError):
            codex_batch.final_response(self.output)

    def test_claude_requires_success_identity_and_nonempty_response(self):
        valid = {"subtype": "success", "is_error": False, "session_id": "conversation", "result": "Final report"}
        self.output.write_text(json.dumps(valid))
        self.assertEqual(claude_batch.final_response(self.output), ("conversation", "Final report"))
        for change in ({"is_error": True}, {"subtype": "error_max_turns"}, {"session_id": None},
                       {"result": "  "}, {"result": []}):
            with self.subTest(change=change):
                self.output.write_text(json.dumps({**valid, **change}))
                with self.assertRaises(ValueError):
                    claude_batch.final_response(self.output)
        for text in ("[]", "{}", "not JSON"):
            self.output.write_text(text)
            with self.assertRaises(ValueError):
                claude_batch.final_response(self.output)


if __name__ == "__main__":
    unittest.main()
