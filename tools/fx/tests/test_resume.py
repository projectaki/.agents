import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


TOOL_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_DIRECTORY))
sys.path.insert(0, str(TOOL_DIRECTORY / "agents"))
from fx_resume import conversation_id, resolve_session, session_metadata
from fx_context import save_response
from fx_events import save_event


class ResumeTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fx resume ")
        self.addCleanup(self.temporary.cleanup)
        self.task = Path(self.temporary.name)
        self.session = self.task / "context/session"
        self.session.mkdir(parents=True)
        for name in ("instructions.md", "input-context.md", "findings.md"):
            (self.session / name).write_text("Preserve this file\n")
        (self.session / "launch.txt").write_text("agent=claude\nreasoning=high\nmodel=original-model\n")

    def event(self, identity="conversation-one", **extra):
        save_event(self.session, "claude", "hook", json.dumps({
            "hook_event_name": "SessionStart", "session_id": identity, **extra,
        }))

    def test_resolves_explicit_session_and_preserves_metadata(self):
        self.assertEqual(resolve_session(self.task, "claude", self.session), self.session)
        self.assertEqual(session_metadata(self.session), {
            "agent": "claude", "reasoning": "high", "model": "original-model",
        })
        self.assertEqual((self.session / "findings.md").read_text(), "Preserve this file\n")

    def test_generated_claude_settings_apply_access_and_preserve_capture_hooks(self):
        for access in ("auto", "full"):
            with self.subTest(access=access):
                (self.session / "access.txt").write_text(access)
                result = subprocess.run([sys.executable, TOOL_DIRECTORY / "agents/claude_capture.py",
                                         "settings", self.session], capture_output=True, text=True, check=True)
                settings = json.loads(result.stdout)
                if access == "full":
                    self.assertIs(settings["sandbox"]["enabled"], False)
                else:
                    self.assertNotIn("sandbox", settings)
                self.assertIn("Stop", settings["hooks"])
                self.assertIn("SessionStart", settings["hooks"])

    def test_disabling_sandbox_preserves_invalid_settings_and_reports_failure(self):
        path = self.session / "claude-settings.json"
        for content in ('{', '[]', '{"sandbox": null}'):
            with self.subTest(content=content):
                path.write_text(content)
                result = subprocess.run([sys.executable, TOOL_DIRECTORY / "agents/claude_capture.py",
                                         "configure-access", self.session], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Cannot configure Claude access", result.stderr)
                self.assertEqual(path.read_text(), content)

    def test_resolves_group_member_and_analysis_sessions(self):
        for directory in ("groups/000001-review/1-claude-model", "analyses/000002-analyze-model"):
            destination = self.task / "context" / directory
            destination.parent.mkdir(parents=True, exist_ok=True)
            self.session.rename(destination)
            self.assertEqual(resolve_session(self.task, "claude", destination), destination)
            destination.rename(self.session)

    def test_rejects_outside_paths_other_agents_and_incomplete_sessions(self):
        with self.assertRaisesRegex(ValueError, "inside this task"):
            resolve_session(self.task, "claude", self.task)
        with self.assertRaisesRegex(ValueError, "different agent"):
            resolve_session(self.task, "codex", self.session)
        (self.session / "instructions.md").unlink()
        with self.assertRaisesRegex(ValueError, "instructions.md"):
            resolve_session(self.task, "claude", self.session)

    def test_rejects_symlink_sessions_and_files(self):
        alias = self.task / "context/alias"
        alias.symlink_to(self.session, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic links"):
            resolve_session(self.task, "claude", alias)
        (self.session / "launch.txt").rename(self.session / "real-launch.txt")
        (self.session / "launch.txt").symlink_to(self.session / "real-launch.txt")
        with self.assertRaisesRegex(ValueError, "regular launch"):
            resolve_session(self.task, "claude", self.session)

    def test_rejects_invalid_saved_model_and_reasoning(self):
        for metadata in ("agent=claude\nreasoning=unknown\nmodel=model", "agent=claude\nreasoning=high\nmodel=bad model"):
            (self.session / "launch.txt").write_text(metadata)
            with self.assertRaises(ValueError):
                session_metadata(self.session)

    def test_recovers_identity_before_a_response_and_ignores_subagents(self):
        self.event()
        self.event("child", agent_id="child-agent")
        save_event(self.session, "codex", "hook", '{"session_id":"other-provider"}')
        self.assertEqual(conversation_id(self.session, "claude"), "conversation-one")
        self.assertFalse((self.session / "results").exists())

    def test_recovers_identity_from_existing_response_metadata(self):
        save_response(self.session, "claude", "conversation-one", "turn-one", "Saved response")
        self.assertEqual(conversation_id(self.session, "claude"), "conversation-one")

    def test_codex_identity_ignores_notifications_and_subagents(self):
        identity = "01900000-0000-7000-8000-000000000001"
        save_response(self.session, "codex", identity, "turn-one", "Saved response")
        for source, payload in (
            ("notify", {"session_id": "notification"}),
            ("hook", {"session_id": "child", "agent_id": "subagent"}),
        ):
            save_event(self.session, "codex", source, json.dumps(payload))
        self.assertEqual(conversation_id(self.session, "codex"), identity)
        save_event(self.session, "codex", "hook", json.dumps({"session_id": "conflicting-session"}))
        with self.assertRaisesRegex(ValueError, "exactly one recorded Codex"):
            conversation_id(self.session, "codex")

    def test_refuses_missing_or_conflicting_identities(self):
        with self.assertRaisesRegex(ValueError, "exactly one"):
            conversation_id(self.session, "claude")
        self.event("one")
        self.event("two")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            conversation_id(self.session, "claude")

    def test_refuses_truncated_callback_log_without_repair(self):
        self.event()
        path = self.session / "events/callbacks.jsonl"
        with path.open("a") as stream:
            stream.write('{"unfinished":')
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "incomplete last record"):
            conversation_id(self.session, "claude")
        self.assertEqual(path.read_bytes(), before)

    def test_refuses_symbolic_links_in_identity_evidence(self):
        self.event()
        path = self.session / "events/callbacks.jsonl"
        path.rename(self.session / "saved.jsonl")
        path.symlink_to(self.session / "saved.jsonl")
        with self.assertRaisesRegex(ValueError, "symbolic links"):
            conversation_id(self.session, "claude")

    def test_access_override_waits_for_the_session_lock(self):
        access = self.session / "access.txt"
        access.write_text("auto\n")
        command = [sys.executable, TOOL_DIRECTORY / "fx_resume.py", "lock", "--access", "full",
                   self.session, sys.executable, "-c", "pass"]
        with (self.session / ".fx-agent.lock").open("w") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already running", result.stderr)
            self.assertEqual(access.read_text(), "auto\n")
        subprocess.run(command, capture_output=True, text=True, check=True)
        self.assertEqual(access.read_text(), "full\n")

    def test_access_override_rejects_a_symbolic_link(self):
        target = self.session / "original-access.txt"
        target.write_text("auto\n")
        (self.session / "access.txt").symlink_to(target)
        result = subprocess.run([
            sys.executable, TOOL_DIRECTORY / "fx_resume.py", "lock", "--access", "full",
            self.session, sys.executable, "-c", "raise AssertionError('must not start')",
        ], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symbolic link", result.stderr)
        self.assertEqual(target.read_text(), "auto\n")

    def test_lock_blocks_duplicate_launch_and_releases_after_exit(self):
        lock = self.session / ".fx-agent.lock"
        with lock.open("w") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run([sys.executable, TOOL_DIRECTORY / "fx_resume.py", "lock",
                                     self.session, sys.executable, "-c", "raise AssertionError('must not start')"],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already running", result.stderr)
        script = "import fcntl, os, sys; fd=os.open(sys.argv[1], os.O_RDWR); fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)"
        result = subprocess.run([sys.executable, TOOL_DIRECTORY / "fx_resume.py", "lock", self.session,
                                 sys.executable, "-c", script, lock], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BlockingIOError", result.stderr)
        with lock.open() as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)


if __name__ == "__main__":
    unittest.main()
