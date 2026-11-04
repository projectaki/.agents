import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

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
                       {"result": "  "}, {"result": []}, {'permission_denials': {}},
                       {'permission_denials': [None]}, {'permission_denials': [{'tool_name': None}]}):
            with self.subTest(change=change):
                self.output.write_text(json.dumps({**valid, **change}))
                with self.assertRaises(ValueError):
                    claude_batch.final_response(self.output)
        for text in ("[]", "{}", "not JSON"):
            self.output.write_text(text)
            with self.assertRaises(ValueError):
                claude_batch.final_response(self.output)

    def test_claude_rejects_results_with_permission_denials(self):
        self.output.write_text(json.dumps({
            'subtype': 'success', 'is_error': False, 'session_id': 'conversation',
            'result': 'I could not read the issue.',
            'permission_denials': [{'tool_name': 'mcp__claude_ai_Linear__get_issue'}],
        }))
        with self.assertRaisesRegex(ValueError, 'permission.*mcp__claude_ai_Linear__get_issue'):
            claude_batch.final_response(self.output)

    def test_claude_batch_uses_auto_review_without_tool_allowlists(self):
        session = self.output.parent / 'session'
        session.mkdir()
        (session / 'instructions.md').write_text('Investigate without editing source.')
        commands = []
        def run(command, **kwargs):
            commands.append(command)
            if '--print' in command:
                kwargs['stdout'].write(json.dumps({
                    'subtype': 'success', 'session_id': 'conversation', 'result': 'Report',
                }))
            return SimpleNamespace(returncode=0)
        project = self.output.parent
        with patch.object(sys, 'argv', ['claude_batch.py', str(project), str(project), str(session), 'medium', 'Investigate']), \
             patch.object(claude_batch.subprocess, 'check_output', return_value='claude-opus-5-5'), \
             patch.object(claude_batch.subprocess, 'run', side_effect=run):
            self.assertEqual(claude_batch.main(), 0)
        command = next(command for command in commands if '--print' in command)
        self.assertIn('--permission-mode', command)
        self.assertEqual(command[command.index('--permission-mode') + 1], 'auto')
        self.assertNotIn('--allowedTools', command)
        self.assertNotIn('--dangerously-skip-permissions', command)
        self.assertIn(str(project), [command[index + 1] for index, value in enumerate(command) if value == '--add-dir'])

    def test_codex_batch_uses_full_access(self):
        session = self.output.parent / 'session'
        session.mkdir()
        (session / 'instructions.md').write_text('Investigate.')
        commands = []
        def run(command, **kwargs):
            commands.append(command)
            if 'exec' in command:
                for event in (
                    {'type': 'thread.started', 'thread_id': 'conversation'},
                    {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'Report'}},
                    {'type': 'turn.completed'},
                ):
                    kwargs['stdout'].write(json.dumps(event) + '\n')
            return SimpleNamespace(returncode=0)
        project = self.output.parent
        with patch.object(sys, 'argv', ['codex_batch.py', str(project), str(project), str(session), 'medium', 'Investigate']), \
             patch.object(codex_batch.subprocess, 'check_output', side_effect=['gpt-6.1-sol', 'notify=[]']), \
             patch.object(codex_batch.subprocess, 'run', side_effect=run):
            self.assertEqual(codex_batch.main(), 0)
        command = next(command for command in commands if 'exec' in command)
        self.assertIn('--dangerously-bypass-approvals-and-sandbox', command)


if __name__ == "__main__":
    unittest.main()
