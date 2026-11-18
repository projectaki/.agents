"""The Claude adapter: the launch command for each mode and access level, the
hook payloads it turns into facts, and the transcript path."""

import json
import shlex
import unittest
from datetime import datetime, timezone
from pathlib import Path

from x_env.harness import TurnBegan, TurnFinished
from x_env.harness.claude import Claude, transcript_path
from x_env.model import Access, HarnessName, ProjectName, SessionId, SessionName, TaskName
from x_env.records import SCHEMA, HarnessBinding, LaunchFacts, SessionMeta

PLUGIN = Path(__file__).resolve().parents[3]  # tools/x-env/tests -> the x plugin folder
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

    def test_loads_the_x_plugin(self):
        argv = list(Claude().command(meta(), HOOK).argv)
        plugin = Path(option(argv, "--plugin-dir"))
        self.assertEqual(plugin, PLUGIN)
        self.assertEqual(json.loads((plugin / ".claude-plugin/plugin.json").read_text())["name"], "x")

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


class ParseHookTest(unittest.TestCase):
    def test_user_prompt_submit_begins_a_turn(self):
        payload = {"hook_event_name": "UserPromptSubmit", "session_id": SESSION_ID,
                   "transcript_path": "/t.jsonl", "prompt_id": "p1", "prompt": "hi"}
        self.assertEqual(Claude().parse_hook(payload), [TurnBegan()])

    def test_stop_finishes_a_turn_with_the_last_message(self):
        payload = {"hook_event_name": "Stop", "session_id": SESSION_ID, "transcript_path": "/t.jsonl",
                   "prompt_id": "p1", "last_assistant_message": "PONG", "stop_hook_active": False}
        self.assertEqual(Claude().parse_hook(payload), [TurnFinished("PONG")])

    def test_stop_while_a_stop_hook_is_active_is_not_a_new_turn(self):
        payload = {"hook_event_name": "Stop", "session_id": SESSION_ID, "transcript_path": "/t.jsonl",
                   "prompt_id": "p1", "last_assistant_message": "PONG", "stop_hook_active": True}
        self.assertEqual(Claude().parse_hook(payload), [])

    def test_stop_without_a_message_records_an_empty_one(self):
        payload = {"hook_event_name": "Stop", "session_id": SESSION_ID, "stop_hook_active": False}
        self.assertEqual(Claude().parse_hook(payload), [TurnFinished("")])

    def test_subagent_events_are_ignored(self):
        for event in ("UserPromptSubmit", "Stop"):
            payload = {"hook_event_name": event, "session_id": SESSION_ID, "agent_id": "a1",
                       "agent_type": "Explore", "last_assistant_message": "sub", "stop_hook_active": False}
            self.assertEqual(Claude().parse_hook(payload), [], event)

    def test_other_events_are_ignored(self):
        for event in ("SessionStart", "SessionEnd", "PreToolUse"):
            self.assertEqual(Claude().parse_hook({"hook_event_name": event, "session_id": SESSION_ID}), [])


class TranscriptPathTest(unittest.TestCase):
    def test_slug_replaces_slashes_and_dots(self):
        self.assertEqual(
            transcript_path(Path("/home/u"), Path("/home/u/.agents/work/p.v2/repo"), SESSION_ID),
            Path(f"/home/u/.claude/projects/-home-u--agents-work-p-v2-repo/{SESSION_ID}.jsonl"),
        )


if __name__ == "__main__":
    unittest.main()
