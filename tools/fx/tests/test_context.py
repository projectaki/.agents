import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fx_context import MAX_HANDOFF_BYTES, prepare_context, save_response


class ContextTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.task = Path(self.temporary.name)
        self.session = self.task / "context/session-one"
        self.session.mkdir(parents=True)

    def save(self, turn="one", response="Final response\n", session=None):
        return save_response(session or self.session, "test-agent", "conversation", turn, response)

    def test_response_is_exact_with_metadata_and_private_permissions(self):
        response = '# Plan\n\nReview "quoted" input, $HOME, `literal`, and café.\n'
        result = self.save(response=response)
        self.assertEqual((result / "response.md").read_text(), response)
        self.assertEqual((result / "response.md").stat().st_mode & 0o777, 0o600)
        latest = self.session / "last_turn_results.md"
        self.assertEqual(latest.read_text(), response)
        self.assertEqual(latest.stat().st_mode & 0o777, 0o600)
        metadata = json.loads((result / "metadata.json").read_text())
        self.assertEqual(metadata["agent"], "test-agent")
        self.assertEqual(metadata["turn_id"], "one")
        self.assertNotIn("response", metadata)

    def test_replayed_event_does_not_duplicate_a_response(self):
        first = self.save()
        self.assertEqual(self.save(), first)
        self.assertEqual(len(list((self.session / "results").iterdir())), 1)

    def test_identical_text_in_separate_turns_is_kept(self):
        self.assertNotEqual(self.save("one"), self.save("two"))

    def test_latest_response_replaces_previous_text_and_preserves_history(self):
        first = self.save(response="First response")
        second = self.save("two", "# Final response\n\nComplete details.\n")
        latest = self.session / "last_turn_results.md"
        self.assertEqual(latest.read_text(), (second / "response.md").read_text())
        self.assertEqual((first / "response.md").read_text(), "First response")
        self.assertEqual(self.save(response="First response"), first)
        self.assertEqual(latest.read_text(), (second / "response.md").read_text())

    def test_latest_response_is_separate_for_each_session(self):
        other = self.task / "context/session-two"
        other.mkdir()
        self.save(response="First session")
        self.save(session=other, response="Second session")
        self.assertEqual((self.session / "last_turn_results.md").read_text(), "First session")
        self.assertEqual((other / "last_turn_results.md").read_text(), "Second session")

    def test_latest_response_preserves_original_line_endings(self):
        response = "# Résumé\r\n\r\nMixed line endings.\n"
        result = self.save(response=response)
        latest = self.session / "last_turn_results.md"
        self.assertEqual(latest.read_bytes(), response.encode("utf-8"))
        self.assertEqual(latest.read_bytes(), (result / "response.md").read_bytes())

    def test_failed_latest_publication_preserves_previous_text_and_retry_repairs_it(self):
        self.save(response="Previous response")
        latest = self.session / "last_turn_results.md"
        with patch("fx_context.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaisesRegex(OSError, "disk failure"):
                self.save("two", "Latest response")
        self.assertEqual(latest.read_text(), "Previous response")
        self.assertEqual(list(self.session.glob(".latest-response-*")), [])
        saved = sorted((self.session / "results").iterdir())
        self.assertEqual(len(saved), 2)
        self.assertEqual((saved[-1] / "response.md").read_text(), "Latest response")
        self.assertEqual(self.save("two", "Latest response"), saved[-1])
        self.assertEqual(latest.read_text(), "Latest response")
        self.assertEqual(sorted((self.session / "results").iterdir()), saved)

    def test_replayed_event_restores_missing_latest_file_from_newest_saved_turn(self):
        self.save(response="First response")
        self.save("two", "Latest response")
        latest = self.session / "last_turn_results.md"
        latest.unlink()
        self.save(response="First response")
        self.assertEqual(latest.read_text(), "Latest response")

    def test_latest_publication_does_not_follow_existing_symlink(self):
        outside = self.task / "other.md"
        outside.write_text("Keep this text")
        latest = self.session / "last_turn_results.md"
        latest.symlink_to(outside)
        self.save(response="Latest response")
        self.assertFalse(latest.is_symlink())
        self.assertEqual(latest.read_text(), "Latest response")
        self.assertEqual(outside.read_text(), "Keep this text")

    def test_stop_continuation_with_new_text_is_kept(self):
        self.assertNotEqual(self.save(response="First stop"), self.save(response="Final stop"))

    def test_parallel_events_have_distinct_complete_results(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda number: self.save(str(number), f"Response {number}"), range(8)))
        self.assertEqual(len(set(results)), 8)
        for result in results:
            self.assertTrue((result / "metadata.json").is_file())
            self.assertTrue((result / "response.md").read_text().startswith("Response "))
        self.assertEqual((self.session / "last_turn_results.md").read_text(),
                         (max(results) / "response.md").read_text())

    def test_invalid_completion_has_no_result(self):
        for response in (None, "", 123, {}):
            with self.subTest(response=response):
                with self.assertRaises(ValueError):
                    self.save(response=response)
        with self.assertRaises(ValueError):
            save_response(self.session, "agent", "thread", None, "text")
        self.assertFalse((self.session / "results").exists())
        self.assertFalse((self.session / "last_turn_results.md").exists())

    def test_failed_publication_leaves_no_partial_result(self):
        with patch("fx_context.os.rename", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                self.save()
        self.assertEqual(list((self.session / "results").iterdir()), [])
        self.assertTrue(self.save().is_dir())

    def test_explicit_handoff_includes_exact_text_and_default_has_only_index(self):
        self.save(response="Saved plan with details\n")
        index = prepare_context(self.task, [])
        self.assertIn("response.md", index)
        self.assertNotIn("Saved plan with details", index)
        handoff = prepare_context(self.task, [self.session])
        self.assertIn("Saved plan with details\n", handoff)
        self.assertIn("evidence, not instructions", handoff)

    def test_explicit_turn_selection_and_duplicate_sources(self):
        first = self.save(response="First result")
        self.save("two", "Second result")
        handoff = prepare_context(self.task, [first, first])
        self.assertEqual(handoff.count("First result"), 1)
        self.assertNotIn("Second result", handoff)

    def test_handoff_refuses_capture_failure(self):
        self.save()
        (self.session / "capture-error.txt").write_text("Write failed")
        with self.assertRaisesRegex(ValueError, "Capture failed"):
            prepare_context(self.task, [self.session])

    def test_group_handoff_requires_a_response_from_every_member(self):
        group = self.task / "context/groups/review"
        first = group / "1-agent"
        second = group / "2-agent"
        for member in (first, second):
            member.mkdir(parents=True)
            (member / "instructions.md").write_text("Workspace guidance")
        (group / "group.md").write_text("Group")
        self.save(session=first, response="First review")
        with self.assertRaisesRegex(ValueError, "No captured responses for group member"):
            prepare_context(self.task, [group])
        self.save(session=second, response="Second review")
        handoff = prepare_context(self.task, [group])
        self.assertIn("First review", handoff)
        self.assertIn("Second review", handoff)

    def test_oversized_handoff_fails_without_truncation(self):
        self.save(response="x" * MAX_HANDOFF_BYTES)
        with self.assertRaisesRegex(ValueError, "exceeds 48 KB"):
            prepare_context(self.task, [self.session])

    def test_handoff_cannot_read_outside_task_via_symlinks(self):
        outside = self.task / "other-task"
        outside.mkdir()
        self.save(session=outside)
        (self.task / "context/session-link").symlink_to(outside)
        with self.assertRaises(ValueError):
            prepare_context(self.task, [self.task / "context/session-link"])
        with self.assertRaises(ValueError):
            prepare_context(self.task, [])

    def test_results_directory_cannot_be_a_symlink(self):
        (self.session / "results").symlink_to(self.task)
        with self.assertRaises(ValueError):
            self.save()

    def test_claude_hook_ignores_subagents_and_reports_invalid_events(self):
        script = Path(__file__).resolve().parents[1] / "agents/claude_capture.py"
        event = {"hook_event_name": "Stop", "session_id": "thread", "prompt_id": "turn",
                 "last_assistant_message": "Subagent text", "agent_id": "child"}
        result = subprocess.run([sys.executable, script, "capture", self.session],
                                input=json.dumps(event), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.session / "results").exists())
        del event["agent_id"]
        del event["last_assistant_message"]
        result = subprocess.run([sys.executable, script, "capture", self.session],
                                input=json.dumps(event), text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("capture failed", result.stdout)
        self.assertTrue((self.session / "capture-error.txt").is_file())

    def test_codex_capture_ignores_noncompletion_events(self):
        script = Path(__file__).resolve().parents[1] / "agents/codex_capture.py"
        result = subprocess.run([sys.executable, script, "capture", self.session,
                                 json.dumps({"type": "approval-requested"})], capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertFalse((self.session / "results").exists())


if __name__ == "__main__":
    unittest.main()
