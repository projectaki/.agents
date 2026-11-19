"""The Codex adapter: the launch command for each mode and access level, the
notify payloads it turns into facts, the binding, the default model, and
`check`."""

import io
import json
import os
import tempfile
import tomllib
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from x_env.harness import Bound, TurnFinished
from x_env.harness.codex import Codex, is_trusted
from x_env.model import Access, HarnessName, ProjectName, SessionId, SessionName, TaskName, XEnvError
from x_env.records import SCHEMA, HarnessBinding, LaunchFacts, SessionMeta

HOOK = ["/usr/bin/python3", "/x/tools/x-env/x-env", "_hook", "codex", "/w/p/sessions/fix/001-probe"]
CWD = Path("/w/p/tasks/fix/repo")
THREAD = "01a1ef16-70d9-74b1-b2ca-8cd052afc14d"
PAYLOAD = {
    "type": "agent-turn-complete", "thread-id": THREAD, "turn-id": "01a1ef16-7a00-7000-8000-000000000001",
    "cwd": str(CWD), "client": "codex_exec", "input-messages": ["Reply with the single word PONG."],
    "last-assistant-message": "PONG",
}


def meta(mode="headless", access=Access.AUTO, prompt="Fix the login bug", effort=None, model="default"):
    return SessionMeta(
        schema=SCHEMA, id=SessionId("fix/001-probe"), project=ProjectName("p"), task=TaskName("fix"),
        name=SessionName("probe"), created_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
        launch=LaunchFacts(
            harness=HarnessName.CODEX, model=model, effort=effort, access=access, mode=mode,
            host="laptop", cwd=CWD, prompt=prompt, binding=None,
        ),
    )


def argv_of(**options):
    return list(Codex().command(meta(**options), HOOK).argv)


def configs(argv):
    """The `-c key=value` overrides, each value parsed as TOML as Codex does."""
    return {
        key: tomllib.loads(f"v = {value}")["v"]
        for flag, setting in zip(argv, argv[1:]) if flag == "-c"
        for key, _, value in [setting.partition("=")]
    }


class FakeHome(unittest.TestCase):
    """A temporary HOME (and PATH), so `Path.home()` points at a fake `~/.codex`."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name) / "home"
        self.bin = Path(temporary.name) / "bin"
        (self.home / ".codex").mkdir(parents=True)
        self.bin.mkdir()
        (self.bin / "codex").write_text("#!/bin/sh\n")
        (self.bin / "codex").chmod(0o755)
        patcher = mock.patch.dict(os.environ, HOME=str(self.home), PATH=str(self.bin))
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_config(self, content):
        (self.home / ".codex/config.toml").write_text(content)


class CommandTest(unittest.TestCase):
    def test_headless_runs_exec_with_the_prompt_last(self):
        argv = argv_of(mode="headless")
        self.assertEqual(argv[:3], ["codex", "exec", "--skip-git-repo-check"])
        self.assertEqual(argv[argv.index("-C") + 1], str(CWD))
        self.assertEqual(argv[-2:], ["--", "Fix the login bug"])

    def test_visible_opens_the_ui_with_the_prompt_as_the_first_message(self):
        argv = argv_of(mode="visible")
        self.assertEqual(argv[0], "codex")
        self.assertNotIn("exec", argv)
        self.assertEqual(argv[-2:], ["--", "Fix the login bug"])

    def test_visible_without_prompt_starts_with_no_message(self):
        argv = argv_of(mode="visible", prompt=None)
        self.assertNotIn("--", argv)

    def test_prompt_that_starts_with_a_dash_stays_a_prompt(self):
        self.assertEqual(argv_of(prompt="--help me")[-2:], ["--", "--help me"])

    def test_access_levels(self):
        for mode in ("headless", "visible"):
            auto, full = argv_of(mode=mode, access=Access.AUTO), argv_of(mode=mode, access=Access.FULL)
            self.assertIn("--approve-for-me", auto)
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", auto)
            self.assertIn("--dangerously-bypass-approvals-and-sandbox", full)
            self.assertNotIn("--approve-for-me", full)

    def test_model_is_passed_unless_it_is_the_default(self):
        self.assertNotIn("-m", argv_of(model="default"))
        argv = argv_of(model="gpt-6.1-sol")
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-6.1-sol")

    def test_effort_only_when_given(self):
        for mode in ("headless", "visible"):
            self.assertNotIn("model_reasoning_effort", configs(argv_of(mode=mode)))
            self.assertEqual(configs(argv_of(mode=mode, effort="high"))["model_reasoning_effort"], "high")

    def test_model_and_effort_together(self):
        argv = argv_of(model="gpt-6.1-sol", effort="low")
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-6.1-sol")
        self.assertEqual(configs(argv)["model_reasoning_effort"], "low")

    def test_notify_calls_x_env_with_the_notify_event(self):
        for mode in ("headless", "visible"):
            self.assertEqual(configs(argv_of(mode=mode))["notify"], [*HOOK, "notify"])

    def test_notify_survives_quotes_backslashes_and_unicode_in_the_record_path(self):
        hook = [*HOOK[:-1], '/w/my "work" \\ $HOME/é 😀/sessions/fix/001-probe']
        argv = list(Codex().command(meta(), hook).argv)
        self.assertEqual(configs(argv)["notify"], [*hook, "notify"])


class ParseHookTest(FakeHome):
    def parse(self, *args):
        return Codex().parse_hook("notify", list(args), io.StringIO("stdin is not the payload"))

    def rollout(self, thread_id=THREAD, thread_source="user", day="2026/11/18"):
        """A rollout file whose first line is a `session_meta`, as Codex writes it."""
        folder = self.home / ".codex/sessions" / day
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"rollout-2026-11-18T14-36-28-{thread_id}.jsonl"
        meta = {"type": "session_meta", "payload": {"id": thread_id, "thread_source": thread_source}}
        path.write_text(json.dumps(meta) + "\n" + json.dumps({"type": "event_msg"}) + "\n")
        return path

    def test_turn_complete_of_the_user_thread_binds_it_then_finishes_a_turn(self):
        self.rollout("01a1ef16-0000-0000-0000-000000000000")  # another thread, same day
        rollout = self.rollout()
        self.assertEqual(self.parse(json.dumps(PAYLOAD)),
                         [Bound(HarnessBinding(THREAD, rollout)), TurnFinished("PONG")])

    def test_the_rollout_is_found_on_any_day(self):
        rollout = self.rollout(day="2026/10/31")
        self.assertEqual(self.parse(json.dumps(PAYLOAD))[0], Bound(HarnessBinding(THREAD, rollout)))

    def test_the_payload_is_the_last_argument(self):
        self.rollout()
        self.assertEqual(self.parse("ignored", json.dumps(PAYLOAD))[1], TurnFinished("PONG"))

    def test_a_thread_without_a_rollout_is_ignored(self):
        """The UI's title-generation thread: its own thread-id, no rollout file."""
        title = {**PAYLOAD, "thread-id": "01a1ef21-ad78-7602-af25-445598eb05d7", "client": "codex-tui",
                 "last-assistant-message": '{"title":"Return PONG"}'}
        self.assertEqual(self.parse(json.dumps(title)), [])

    def test_a_subagent_thread_is_ignored(self):
        self.rollout(thread_source="subagent")
        self.assertEqual(self.parse(json.dumps(PAYLOAD)), [])

    def test_an_unreadable_rollout_is_not_a_user_thread(self):
        self.rollout().write_text("not json\n")
        self.assertEqual(self.parse(json.dumps(PAYLOAD)), [])

    def test_other_types_are_ignored(self):
        self.rollout()
        self.assertEqual(self.parse(json.dumps({**PAYLOAD, "type": "approval-requested"})), [])

    def test_bad_payloads_are_errors(self):
        self.rollout()
        for args in ([], ["not json"], ["[1, 2]"], [json.dumps({**PAYLOAD, "thread-id": "../*"})],
                     [json.dumps({k: v for k, v in PAYLOAD.items() if k != "thread-id"})]):
            with self.assertRaises(ValueError, msg=args):
                self.parse(*args)


class IsTrustedTest(unittest.TestCase):
    CLONE = Path("/w/p/repo/main")

    def config(self, path="/w/p/repo/main", **entry):
        return {"projects": {path: entry}}

    def test_trusted(self):
        self.assertTrue(is_trusted(self.config(trust_level="trusted"), self.CLONE))

    def test_other_trust_level(self):
        self.assertFalse(is_trusted(self.config(trust_level="untrusted"), self.CLONE))

    def test_missing_projects_table(self):
        self.assertFalse(is_trusted({}, self.CLONE))

    def test_other_path(self):
        self.assertFalse(is_trusted(self.config("/w/other/repo/main", trust_level="trusted"), self.CLONE))


class DefaultModelTest(FakeHome):
    def test_the_configured_model(self):
        self.write_config('model = "gpt-6.1-sol"\nmodel_reasoning_effort = "medium"\n')
        self.assertEqual(Codex().default_model(), "gpt-6.1-sol")

    def test_default_without_a_model_in_the_config(self):
        self.assertEqual(Codex().default_model(), "default")  # no config.toml
        self.write_config("not = [toml")
        self.assertEqual(Codex().default_model(), "default")
        self.write_config('[tui]\nmodel = "nested, not top-level"\n')
        self.assertEqual(Codex().default_model(), "default")


class CheckTest(FakeHome):
    INSTALLED = '[plugins."x@amx-plugins"]\nenabled = true\n'

    def test_passes_when_the_cli_and_the_x_plugin_are_installed(self):
        self.write_config(self.INSTALLED)
        Codex().check()

    def test_fails_when_the_cli_is_missing(self):
        (self.bin / "codex").unlink()
        self.write_config(self.INSTALLED)
        with self.assertRaisesRegex(XEnvError, "codex CLI is not on PATH"):
            Codex().check()

    def test_fails_with_an_install_hint_when_the_x_plugin_is_not_installed(self):
        for content in (None, "not = [toml", '[plugins."github@openai-curated"]\nenabled = true\n',
                        '[plugins."x@amx-plugins"]\nenabled = false\n'):
            if content is not None:
                self.write_config(content)
            with self.assertRaisesRegex(XEnvError, "codex plugin add x@", msg=content):
                Codex().check()


if __name__ == "__main__":
    unittest.main()
