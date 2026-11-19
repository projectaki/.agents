"""The Claude adapter: the launch command for each mode and access level, the
hook payloads it turns into facts, the transcript path, and `check`."""

import io
import json
import os
import shlex
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timezone
from pathlib import Path

from x_env.harness import TurnBegan, TurnFinished
from x_env.harness.claude import Claude, is_trusted, transcript_path, trust_folder, with_trust
from x_env.model import Access, HarnessName, XEnvError, ProjectName, SessionId, SessionName, TaskName
from x_env.records import SCHEMA, HarnessBinding, LaunchFacts, SessionMeta

HOOK = ["/usr/bin/python3", "/x/tools/x-env/x-env", "_hook", "claude", "/w/p/sessions/fix/001-chief"]
SESSION_ID = "0b5bfb4e-7a5a-4a39-9d55-2d1c7e1e7d0e"


def meta(mode="headless", access=Access.AUTO, prompt="Fix the login bug", effort=None, model="haiku"):
    return SessionMeta(
        schema=SCHEMA, id=SessionId("fix/001-chief"), project=ProjectName("p"), task=TaskName("fix"),
        name=SessionName("chief"), created_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
        launch=LaunchFacts(
            harness=HarnessName.CLAUDE, model=model, effort=effort, access=access, mode=mode,
            host="laptop", cwd=Path("/w/p/tasks/fix/repo"), prompt=prompt,
            binding=HarnessBinding(SESSION_ID, Path("/home/u/.claude/projects/x/s.jsonl")),
        ),
    )


def option(argv, name):
    return argv[argv.index(name) + 1]


class CommandTest(unittest.TestCase):
    def test_headless_runs_print_mode_with_the_prompt_last(self):
        argv = list(Claude().command(meta(mode="headless"), HOOK).argv)
        self.assertEqual(argv[0], "claude")
        self.assertIn("-p", argv)
        self.assertEqual(argv[-2:], ["--", "Fix the login bug"])
        self.assertEqual(option(argv, "--session-id"), SESSION_ID)
        self.assertEqual(option(argv, "--model"), "haiku")

    def test_visible_passes_the_prompt_as_the_first_message(self):
        argv = list(Claude().command(meta(mode="visible"), HOOK).argv)
        self.assertNotIn("-p", argv)
        self.assertEqual(argv[-2:], ["--", "Fix the login bug"])

    def test_visible_without_prompt_starts_with_no_message(self):
        argv = list(Claude().command(meta(mode="visible", prompt=None), HOOK).argv)
        self.assertNotIn("-p", argv)
        self.assertNotIn("--", argv)

    def test_prompt_that_starts_with_a_dash_stays_a_prompt(self):
        argv = list(Claude().command(meta(prompt="--help me"), HOOK).argv)
        self.assertEqual(argv[-2:], ["--", "--help me"])

    def test_access_auto(self):
        argv = list(Claude().command(meta(access=Access.AUTO), HOOK).argv)
        self.assertEqual(option(argv, "--permission-mode"), "auto")
        self.assertNotIn("sandbox", json.loads(option(argv, "--settings")))

    def test_access_full_bypasses_permissions_and_the_sandbox(self):
        argv = list(Claude().command(meta(access=Access.FULL), HOOK).argv)
        self.assertEqual(option(argv, "--permission-mode"), "bypassPermissions")
        self.assertEqual(json.loads(option(argv, "--settings"))["sandbox"], {"enabled": False})

    def test_effort_only_when_given(self):
        self.assertNotIn("--effort", Claude().command(meta(effort=None), HOOK).argv)
        argv = list(Claude().command(meta(effort="high"), HOOK).argv)
        self.assertEqual(option(argv, "--effort"), "high")

    def test_relies_on_the_installed_x_plugin(self):
        self.assertNotIn("--plugin-dir", Claude().command(meta(), HOOK).argv)

    def test_installs_turn_hooks_that_call_x_env_with_the_event(self):
        settings = json.loads(option(list(Claude().command(meta(), HOOK).argv), "--settings"))
        self.assertEqual(set(settings["hooks"]), {"UserPromptSubmit", "Stop"})
        for event, groups in settings["hooks"].items():
            [group] = groups
            [hook] = group["hooks"]
            self.assertEqual(hook["type"], "command")
            self.assertEqual(shlex.split(hook["command"]), [*HOOK, event])

    def test_hook_command_survives_shell_characters_in_the_record_path(self):
        hook = [*HOOK[:-1], '/w/my "work" $HOME/p/sessions/fix/001-chief']
        settings = json.loads(option(list(Claude().command(meta(), hook).argv), "--settings"))
        command = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
        self.assertEqual(shlex.split(command), [*hook, "Stop"])


def parse(payload, event="Stop"):
    """Call the hook the way `x-env _hook claude <record> <event>` does: the
    payload on stdin, no extra arguments."""
    return Claude().parse_hook(event, [], io.StringIO(json.dumps(payload)))


class ParseHookTest(unittest.TestCase):
    def test_user_prompt_submit_begins_a_turn(self):
        payload = {"hook_event_name": "UserPromptSubmit", "session_id": SESSION_ID,
                   "transcript_path": "/t.jsonl", "prompt_id": "p1", "prompt": "hi"}
        self.assertEqual(parse(payload), [TurnBegan()])

    def test_stop_finishes_a_turn_with_the_last_message(self):
        payload = {"hook_event_name": "Stop", "session_id": SESSION_ID, "transcript_path": "/t.jsonl",
                   "prompt_id": "p1", "last_assistant_message": "PONG", "stop_hook_active": False}
        self.assertEqual(parse(payload), [TurnFinished("PONG")])

    def test_stop_while_a_stop_hook_is_active_is_not_a_new_turn(self):
        payload = {"hook_event_name": "Stop", "session_id": SESSION_ID, "transcript_path": "/t.jsonl",
                   "prompt_id": "p1", "last_assistant_message": "PONG", "stop_hook_active": True}
        self.assertEqual(parse(payload), [])

    def test_stop_without_a_message_records_an_empty_one(self):
        payload = {"hook_event_name": "Stop", "session_id": SESSION_ID, "stop_hook_active": False}
        self.assertEqual(parse(payload), [TurnFinished("")])

    def test_subagent_events_are_ignored(self):
        for event in ("UserPromptSubmit", "Stop"):
            payload = {"hook_event_name": event, "session_id": SESSION_ID, "agent_id": "a1",
                       "agent_type": "Explore", "last_assistant_message": "sub", "stop_hook_active": False}
            self.assertEqual(parse(payload), [], event)

    def test_the_event_argument_names_a_payload_without_hook_event_name(self):
        self.assertEqual(parse({"session_id": SESSION_ID}, event="UserPromptSubmit"), [TurnBegan()])

    def test_a_payload_that_is_not_a_json_object_is_an_error(self):
        for raw in ("not json", "[1, 2]"):
            with self.assertRaises(ValueError, msg=raw):
                Claude().parse_hook("Stop", [], io.StringIO(raw))

    def test_other_events_are_ignored(self):
        for event in ("SessionStart", "SessionEnd", "PreToolUse"):
            self.assertEqual(parse({"hook_event_name": event, "session_id": SESSION_ID}), [])


class TranscriptPathTest(unittest.TestCase):
    def test_slug_replaces_slashes_and_dots(self):
        self.assertEqual(
            transcript_path(Path("/home/u"), Path("/home/u/.agents/work/p.v2/repo"), SESSION_ID),
            Path(f"/home/u/.claude/projects/-home-u--agents-work-p-v2-repo/{SESSION_ID}.jsonl"),
        )


class TrustTest(unittest.TestCase):
    ROOT = Path("/home/u/work")

    def test_trusted_root(self):
        config = {"projects": {"/home/u/work": {"hasTrustDialogAccepted": True}}}
        self.assertTrue(is_trusted(config, self.ROOT))

    def test_parent_does_not_count(self):
        config = {"projects": {"/home/u": {"hasTrustDialogAccepted": True}}}
        self.assertFalse(is_trusted(config, self.ROOT))

    def test_untrusted(self):
        config = {"projects": {"/home/other": {"hasTrustDialogAccepted": True}}}
        self.assertFalse(is_trusted(config, self.ROOT))

    def test_trust_false(self):
        config = {"projects": {"/home/u/work": {"hasTrustDialogAccepted": False}}}
        self.assertFalse(is_trusted(config, self.ROOT))

    def test_missing_projects_key(self):
        self.assertFalse(is_trusted({}, self.ROOT))


class WithTrustTest(unittest.TestCase):
    FOLDER = Path("/w/p/tasks/t/repo")

    def test_new_file(self):
        self.assertEqual(with_trust({}, self.FOLDER), {"projects": {str(self.FOLDER): {"hasTrustDialogAccepted": True}}})

    def test_new_entry_keeps_other_projects_and_keys(self):
        config = {"a": 1, "projects": {"/other": {"x": 1}}}
        result = with_trust(config, self.FOLDER)
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["projects"]["/other"], {"x": 1})
        self.assertTrue(result["projects"][str(self.FOLDER)]["hasTrustDialogAccepted"])
        self.assertNotIn(str(self.FOLDER), config["projects"])

    def test_existing_entry_keeps_other_keys(self):
        config = {"projects": {str(self.FOLDER): {"hasTrustDialogAccepted": False, "allowedTools": ["x"]}}}
        entry = with_trust(config, self.FOLDER)["projects"][str(self.FOLDER)]
        self.assertEqual(entry, {"hasTrustDialogAccepted": True, "allowedTools": ["x"]})


class TrustFolderTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name).resolve()
        self.folder = self.home / "w" / "repo"
        self.path = self.home / ".claude.json"

    def config(self):
        return json.loads(self.path.read_text())

    def test_creates_the_file_with_only_projects(self):
        trust_folder(self.home, self.folder)
        self.assertEqual(self.config(), {"projects": {str(self.folder): {"hasTrustDialogAccepted": True}}})

    def test_keeps_other_keys_and_permissions(self):
        self.path.write_text(json.dumps({"theme": "dark"}))
        self.path.chmod(0o640)
        trust_folder(self.home, self.folder)
        self.assertEqual(self.config()["theme"], "dark")
        self.assertTrue(self.config()["projects"][str(self.folder)]["hasTrustDialogAccepted"])
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o640)
        self.assertEqual([p.name for p in self.home.iterdir()], [".claude.json"])

    def test_bad_json_is_untouched(self):
        for text in ("not json", "[1]"):
            self.path.write_text(text)
            with self.assertLogs("x_env", "WARNING") as logs:
                trust_folder(self.home, self.folder)
            self.assertEqual(len(logs.records), 1)
            self.assertEqual(self.path.read_text(), text)

    def test_already_trusted_leaves_the_file_alone(self):
        self.path.write_text(json.dumps({"projects": {str(self.folder): {"hasTrustDialogAccepted": True}}}))
        os.utime(self.path, (1000, 1000))
        trust_folder(self.home, self.folder)
        self.assertEqual(self.path.stat().st_mtime, 1000)

    def test_retries_when_another_writer_loses_the_change(self):
        real, calls = os.replace, []

        def lossy(source, destination):
            calls.append(source)
            if len(calls) == 1:
                os.unlink(source)  # the other writer wins: our change is lost
                self.path.write_text("{}")
            else:
                real(source, destination)

        with mock.patch("os.replace", lossy):
            trust_folder(self.home, self.folder)
        self.assertEqual(len(calls), 2)
        self.assertTrue(self.config()["projects"][str(self.folder)]["hasTrustDialogAccepted"])

    def test_gives_up_with_one_warning(self):
        with mock.patch("os.replace", lambda s, d: os.unlink(s)), self.assertLogs("x_env", "WARNING") as logs:
            self.path.write_text("{}")
            trust_folder(self.home, self.folder)
        self.assertEqual(len(logs.records), 1)


class CheckTest(unittest.TestCase):
    """`check` with a fake HOME and a PATH that has or lacks `claude`."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name) / "home"
        self.bin = Path(temporary.name) / "bin"
        self.home.mkdir()
        self.bin.mkdir()
        (self.bin / "claude").write_text("#!/bin/sh\n")
        (self.bin / "claude").chmod(0o755)
        patcher = mock.patch.dict(os.environ, HOME=str(self.home), PATH=str(self.bin))
        patcher.start()
        self.addCleanup(patcher.stop)

    def install(self, content):
        path = self.home / ".claude/plugins/installed_plugins.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def test_passes_when_the_cli_and_the_x_plugin_are_installed(self):
        self.install(json.dumps({"version": 2, "plugins": {"x@amx-plugins": [{"scope": "user"}]}}))
        Claude().check()

    def test_fails_when_the_cli_is_missing(self):
        (self.bin / "claude").unlink()
        self.install(json.dumps({"version": 2, "plugins": {"x@amx-plugins": [{"scope": "user"}]}}))
        with self.assertRaisesRegex(XEnvError, "claude CLI is not on PATH"):
            Claude().check()

    def test_fails_with_an_install_hint_when_the_x_plugin_is_not_installed(self):
        for content in (None, "not json", json.dumps({"plugins": {"xx@m": [{}], "other@m": [{}]}}),
                        json.dumps({"plugins": {"x@amx-plugins": []}})):
            if content is not None:
                self.install(content)
            with self.assertRaisesRegex(XEnvError, "claude plugin install x@", msg=content):
                Claude().check()


if __name__ == "__main__":
    unittest.main()
