"""Session integration tests: the `x-env` CLI with a fake `claude`, a fake
`codex`, and a fake `rex` on PATH (tests/fakes). The fake claude calls the
`--settings` hooks and the fake codex calls the `notify` command, each with
real payload shapes, so these tests cover the runner, the hooks, the
records, `wait`, and `delete` stopping sessions, end to end. The fake HOME
has the x plugin installed in both harnesses."""

import json
import os
import signal
import time
import uuid
from pathlib import Path

from test_cli import CliTest

FAKES = Path(__file__).resolve().parent / "fakes"


class SessionTest(CliTest):
    def setUp(self):
        super().setUp()
        for name in ("claude", "codex", "rex"):  # never the real ones: a real rex would open tabs
            (self.bin / name).symlink_to(FAKES / name)
        self.state = self.root / "fake-state"
        self.state.mkdir()
        self.env.update(FAKE_CLAUDE_STATE=str(self.state), FAKE_CODEX_STATE=str(self.state),
                        FAKE_REX_STATE=str(self.state), FAKE_REX_SERVER="0")
        installed = self.home / ".claude/plugins/installed_plugins.json"
        installed.parent.mkdir(parents=True)
        installed.write_text(json.dumps({"version": 2, "plugins": {"x@amx-plugins": [{"scope": "user"}]}}))
        (self.home / ".codex").mkdir()
        (self.home / ".codex/config.toml").write_text('[plugins."x@amx-plugins"]\nenabled = true\n')
        self.addCleanup(self.kill_leftovers)
        self.task_dir = self.task()
        self.sessions = self.task_dir.parent.parent / "sessions"

    def kill_leftovers(self):
        pids = [self.fake_pid()] + [e["pid"] for r in self.sessions.glob("*/*") for e in self.events(r)
                                           if e["event"] == "started"]
        for pid in pids:
            if pid is not None:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    # --- helpers --------------------------------------------------------------

    def start(self, *arguments, cwd=None):
        result = self.x_env(*arguments, cwd=cwd or self.task_dir)
        session_id = result.stdout.strip()
        self.assertRegex(session_id, r"^fix-login/\d{3}-[a-z0-9-]+$")
        return session_id, result

    def record(self, session_id):
        return self.sessions / session_id

    def events(self, record):
        path = record / "events.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def kinds(self, record):
        return [event["event"] for event in self.events(record)]

    def meta(self, record):
        return json.loads((record / "session.json").read_text())

    def fake_argv(self):
        return json.loads((self.state / "argv.json").read_text())

    def fake_pid(self):
        path = self.state / "pid"
        return int(path.read_text()) if path.exists() else None

    def wait_until(self, predicate, timeout=15):
        deadline = time.monotonic() + timeout
        while not predicate():
            if time.monotonic() > deadline:
                self.fail("Timed out")
            time.sleep(0.05)

    def alive(self, pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        stat = Path(f"/proc/{pid}/stat").read_text()
        return stat.rpartition(")")[2].split()[0] != "Z"

    def rex_calls(self):
        path = self.state / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


class RunHeadlessTest(SessionTest):
    def test_run_then_wait_writes_the_records(self):
        session_id, _ = self.start("run", "--headless", "--agent", "claude", "--name", "probe",
                                   "--model", "haiku", "--prompt", "Reply PONG")
        self.assertEqual(session_id, "fix-login/001-probe")
        waited = self.x_env("wait", session_id, cwd=self.task_dir)
        record = self.record(session_id)
        self.assertEqual(waited.stdout.strip(), str(record / "last-turn.md"))

        meta = self.meta(record)
        launch = meta["launch"]
        self.assertEqual((meta["id"], meta["task"], meta["name"]), (session_id, "fix-login", "probe"))
        self.assertEqual(
            (launch["harness"], launch["model"], launch["access"], launch["mode"], launch["prompt"]),
            ("claude", "haiku", "auto", "headless", "Reply PONG"),
        )
        self.assertEqual(launch["cwd"], str(self.task_dir / "repo"))
        session = launch["binding"]["session_id"]
        uuid.UUID(session)
        slug = str(self.task_dir / "repo").replace("/", "-").replace(".", "-")
        self.assertEqual(launch["binding"]["transcript"], str(self.home / ".claude/projects" / slug / f"{session}.jsonl"))
        self.assertEqual(self.fake_argv()[self.fake_argv().index("--session-id") + 1], session)

        events = self.events(record)
        self.assertEqual([e["event"] for e in events], ["started", "turn_started", "turn_end", "exited"])
        self.assertEqual((events[0]["terminal"], events[0]["terminal_handle"]), ("none", None))
        self.assertEqual(events[2]["turn"], 1)  # the subagent Stop and the held-open Stop add no turn
        self.assertEqual(events[3]["exit_code"], 0)
        self.assertEqual((record / "last-turn.md").read_text(), "PONG to Reply PONG")
        output = (record / "output.log").read_text()
        self.assertIn("PONG to Reply PONG", output)
        self.assertIn("fake claude: stderr line", output)
        self.assertNotIn("hook", output)  # every hook exited 0 and printed nothing
        self.assertFalse((record / "hook-error.log").exists())

    def test_wait_passes_the_exit_code_through(self):
        self.env["FAKE_CLAUDE_EXIT"] = "7"
        session_id, _ = self.start("run", "--headless", "--agent", "claude", "--name", "probe", "--prompt", "x")
        waited = self.x_env("wait", session_id, cwd=self.task_dir, check=False)
        self.assertEqual(waited.returncode, 7, waited.stderr)
        self.assertEqual(waited.stdout.strip(), str(self.record(session_id) / "last-turn.md"))
        last = self.events(self.record(session_id))[-1]
        self.assertEqual((last["event"], last["exit_code"]), ("exited", 7))

    def test_sessions_are_numbered_and_found_with_task_option(self):
        project = self.task_dir.parent.parent
        first, _ = self.start("run", "--headless", "--agent", "claude", "--name", "a", "--prompt", "x",
                              "--task", "fix-login", cwd=project)
        second, _ = self.start("run", "--headless", "--agent", "claude", "--name", "b", "--prompt", "x")
        self.assertEqual((first, second), ("fix-login/001-a", "fix-login/002-b"))
        for session_id in (first, second):
            self.x_env("wait", session_id, cwd=project)

    def test_access_default_comes_from_config_and_the_option_wins(self):
        config = self.home / ".config/x-env/config.toml"
        config.parent.mkdir(parents=True)
        config.write_text('[this]\nhost = "box"\naccess = "full"\n')
        session_id, _ = self.start("run", "--headless", "--agent", "claude", "--name", "a", "--prompt", "x")
        self.x_env("wait", session_id, cwd=self.task_dir)
        launch = self.meta(self.record(session_id))["launch"]
        self.assertEqual((launch["access"], launch["host"]), ("full", "box"))
        argv = self.fake_argv()
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "bypassPermissions")

        session_id, _ = self.start("run", "--headless", "--agent", "claude", "--name", "b", "--prompt", "x",
                                   "--access", "auto")
        self.x_env("wait", session_id, cwd=self.task_dir)
        self.assertEqual(self.meta(self.record(session_id))["launch"]["access"], "auto")

    def test_run_needs_a_prompt_and_a_task(self):
        self.assert_fails(self.x_env("run", "--headless", "--agent", "claude", "--name", "a",
                                     cwd=self.task_dir, check=False), "--prompt", code=2)
        self.assert_fails(self.x_env("run", "--headless", "--agent", "claude", "--name", "a", "--prompt", "x",
                                     cwd=self.task_dir.parent.parent, check=False), "--task")
        self.assertFalse((self.sessions / "fix-login").exists())

    def test_missing_claude_fails_before_any_record(self):
        (self.bin / "claude").unlink()
        self.env["PATH"] = f"{self.bin}:/usr/bin:/bin"
        result = self.x_env("run", "--headless", "--agent", "claude", "--name", "a", "--prompt", "x",
                            cwd=self.task_dir, check=False)
        self.assert_fails(result, "claude CLI is not on PATH")
        self.assertFalse((self.sessions / "fix-login").exists())


class CodexHeadlessTest(SessionTest):
    def run_codex(self, *options):
        session_id, _ = self.start("run", "--headless", "--agent", "codex", "--name", "probe",
                                   "--prompt", "Reply PONG", *options)
        return session_id, self.x_env("wait", session_id, cwd=self.task_dir, check=False)

    def test_run_then_wait_writes_the_records(self):
        (self.home / ".codex/config.toml").write_text(
            'model = "gpt-6.1-sol"\n[plugins."x@amx-plugins"]\nenabled = true\n')
        session_id, waited = self.run_codex("--effort", "high")
        self.assertEqual(waited.returncode, 0, waited.stderr)
        record = self.record(session_id)
        self.assertEqual(waited.stdout.strip(), str(record / "last-turn.md"))

        launch = self.meta(record)["launch"]
        self.assertEqual(
            (launch["harness"], launch["model"], launch["effort"], launch["access"], launch["mode"]),
            ("codex", "gpt-6.1-sol", "high", "auto", "headless"),
        )
        argv = self.fake_argv()
        self.assertEqual(argv[:2], ["exec", "--skip-git-repo-check"])
        self.assertEqual(argv[argv.index("-m") + 1], "gpt-6.1-sol")
        [rollout] = (self.home / ".codex/sessions").glob("*/*/*/rollout-*.jsonl")
        thread_id = json.loads(rollout.read_text())["payload"]["id"]
        self.assertEqual(launch["binding"], {"session_id": thread_id, "transcript": str(rollout)})

        events = self.events(record)
        self.assertEqual([e["event"] for e in events], ["started", "turn_end", "exited"])
        self.assertEqual((events[1]["turn"], events[2]["exit_code"]), (1, 0))
        self.assertEqual((record / "last-turn.md").read_text(), "PONG to Reply PONG")
        output = (record / "output.log").read_text()
        self.assertIn(f"session id: {thread_id}", output)
        self.assertIn("PONG to Reply PONG", output)
        self.assertNotIn("notify", output)  # the notify command exited 0 and printed nothing
        self.assertFalse((record / "hook-error.log").exists())

    def test_without_a_configured_model_codex_picks_and_the_record_says_default(self):
        session_id, _ = self.run_codex()
        self.assertEqual(self.meta(self.record(session_id))["launch"]["model"], "default")
        self.assertNotIn("-m", self.fake_argv())

    def test_wait_passes_a_nonzero_exit_through(self):
        self.env["FAKE_CODEX_EXIT"] = "3"
        session_id, waited = self.run_codex()
        self.assertEqual(waited.returncode, 3, waited.stderr)
        record = self.record(session_id)
        self.assertEqual(self.kinds(record), ["started", "turn_end", "exited"])
        self.assertEqual(self.events(record)[-1]["exit_code"], 3)

    def test_missing_x_plugin_fails_before_any_record(self):
        (self.home / ".codex/config.toml").write_text('model = "gpt-6.1-sol"\n')
        result = self.x_env("run", "--headless", "--agent", "codex", "--name", "a", "--prompt", "x",
                            cwd=self.task_dir, check=False)
        self.assert_fails(result, "x plugin is not installed in Codex")
        self.assertFalse((self.sessions / "fix-login").exists())

    def test_a_turn_of_another_user_thread_adds_no_turn(self):
        session_id, _ = self.run_codex()
        record = self.record(session_id)
        bound = self.meta(record)["launch"]["binding"]
        other = "01a1ef21-0000-7000-8000-000000000000"
        rollout = Path(bound["transcript"]).with_name(f"rollout-2026-11-18T00-00-00-{other}.jsonl")
        rollout.write_text(json.dumps({"type": "session_meta", "payload": {"thread_source": "user"}}) + "\n")
        payload = {"type": "agent-turn-complete", "thread-id": other, "last-assistant-message": "other"}
        hook = self.x_env("_hook", "codex", record, "notify", json.dumps(payload))
        self.assertEqual((hook.returncode, hook.stdout), (0, ""))
        self.assertIn("already bound", (record / "hook-error.log").read_text())
        self.assertEqual(self.meta(record)["launch"]["binding"], bound)
        self.assertEqual(self.kinds(record), ["started", "turn_end", "exited"])
        self.assertEqual((record / "last-turn.md").read_text(), "PONG to Reply PONG")

    def test_a_bad_notify_payload_is_logged_and_the_hook_exits_0(self):
        session_id, _ = self.run_codex()
        record = self.record(session_id)
        hook = self.x_env("_hook", "codex", record, "notify", "not json")
        self.assertEqual((hook.returncode, hook.stdout), (0, ""))
        self.assertIn("JSONDecodeError", (record / "hook-error.log").read_text())
        self.assertEqual(self.kinds(record), ["started", "turn_end", "exited"])


class DeleteStopsSessionsTest(SessionTest):
    def test_delete_stops_a_running_headless_session(self):
        self.env["FAKE_CLAUDE_SLEEP"] = "60"
        session_id, _ = self.start("run", "--headless", "--agent", "claude", "--name", "probe", "--prompt", "x")
        record = self.record(session_id)
        self.wait_until(lambda: "turn_started" in self.kinds(record))
        claude_pid = self.fake_pid()
        runner_pid = self.events(record)[0]["pid"]
        self.assertTrue(self.alive(claude_pid))

        deleted = self.x_env("delete", "fix-login", cwd=self.task_dir.parent.parent, check=False)
        self.assertEqual(deleted.returncode, 0, deleted.stderr)
        self.assertIn(f"Stopping session {session_id}", deleted.stderr)
        self.assertEqual(self.kinds(record), ["started", "turn_started", "exited"])
        self.assertEqual(self.events(record)[-1]["exit_code"], 128 + signal.SIGTERM)
        self.wait_until(lambda: not self.alive(claude_pid) and not self.alive(runner_pid), timeout=5)
        self.assertFalse(self.task_dir.exists())
        self.assertTrue((record / "session.json").is_file())  # records outlive the task

    def test_delete_ignores_finished_sessions(self):
        session_id, _ = self.start("run", "--headless", "--agent", "claude", "--name", "probe", "--prompt", "x")
        self.x_env("wait", session_id, cwd=self.task_dir)
        deleted = self.x_env("delete", "fix-login", cwd=self.task_dir.parent.parent)
        self.assertNotIn("Stopping", deleted.stderr)


class ListSessionsTest(SessionTest):
    def run_and_wait(self, task_dir, harness):
        session_id = self.x_env("run", "--headless", "--agent", harness, "--name", "probe", "--prompt", "x",
                                cwd=task_dir).stdout.strip()
        self.x_env("wait", session_id, cwd=task_dir)
        return session_id

    def turn_end_at(self, session_id):
        [end] = [e["at"] for e in self.events(self.record(session_id)) if e["event"] == "turn_end"]
        return end

    def test_lists_every_task_of_the_project_and_one_task_with_the_option(self):
        project = self.task_dir.parent.parent
        other_dir = self.task(project, "add-cache")
        codex_id = self.run_and_wait(other_dir, "codex")
        claude_id = self.run_and_wait(self.task_dir, "claude")
        self.assertEqual((codex_id, claude_id), ("add-cache/001-probe", "fix-login/001-probe"))
        codex_line = f"add-cache/001-probe\tcodex\theadless\tfinished\t1\t{self.turn_end_at(codex_id)}\n"
        claude_line = f"fix-login/001-probe\tclaude\theadless\tfinished\t1\t{self.turn_end_at(claude_id)}\n"

        listed = self.x_env("ls", cwd=self.task_dir)  # the whole project, not only the task of the folder
        self.assertEqual((listed.stdout, listed.returncode), (codex_line + claude_line, 0))
        self.assertRegex(self.turn_end_at(claude_id), r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")
        self.assertEqual(self.x_env("ls", "--task", "fix-login", cwd=project).stdout, claude_line)

    def test_a_record_without_events_is_prepared(self):
        session_id = self.run_and_wait(self.task_dir, "claude")
        (self.record(session_id) / "events.jsonl").unlink()  # as if the runner never started
        listed = self.x_env("ls", cwd=self.task_dir)
        self.assertEqual(listed.stdout, "fix-login/001-probe\tclaude\theadless\tprepared\t0\t-\n")

    def test_a_held_open_session_is_running(self):
        self.env["FAKE_CLAUDE_SLEEP"] = "60"
        session_id, _ = self.start("run", "--headless", "--agent", "claude", "--name", "probe", "--prompt", "x")
        self.wait_until(lambda: "turn_started" in self.kinds(self.record(session_id)))
        listed = self.x_env("ls", cwd=self.task_dir)
        self.assertEqual(listed.stdout, "fix-login/001-probe\tclaude\theadless\trunning\t0\t-\n")

    def test_an_unreadable_record_is_reported_and_the_others_are_listed(self):
        first = self.run_and_wait(self.task_dir, "claude")
        second = self.x_env("run", "--headless", "--agent", "claude", "--name", "other", "--prompt", "x",
                            cwd=self.task_dir).stdout.strip()
        self.x_env("wait", second, cwd=self.task_dir)
        broken = self.record(first) / "session.json"
        broken.write_text("{")
        listed = self.x_env("ls", cwd=self.task_dir, check=False)
        self.assertEqual(listed.returncode, 1)
        self.assertEqual(listed.stdout,
                         f"fix-login/002-other\tclaude\theadless\tfinished\t1\t{self.turn_end_at(second)}\n")
        self.assertIn(f"x-env: Unreadable session record: {broken}", listed.stderr)

    def test_an_unknown_task_lists_nothing(self):
        self.run_and_wait(self.task_dir, "claude")
        listed = self.x_env("ls", "--task", "no-such-task", cwd=self.task_dir)
        self.assertEqual((listed.stdout, listed.returncode), ("", 0))


class VisibleTest(SessionTest):
    def test_agent_runs_headless_without_a_rex_server(self):
        session_id, started = self.start("agent", "--agent", "claude", "--name", "helper", "--prompt", "hi")
        self.assertEqual(started.stderr.count("No Rex server; the session runs headless."), 1)
        self.assertEqual(self.x_env("wait", session_id, cwd=self.task_dir).returncode, 0)
        record = self.record(session_id)
        self.assertEqual(self.meta(record)["launch"]["mode"], "headless")
        self.assertIn("-p", self.fake_argv())
        self.assertEqual(self.events(record)[0]["terminal"], "none")
        self.assertFalse((self.state / "server-started").exists())

    def test_agent_without_rex_and_without_prompt_is_refused(self):
        result = self.x_env("agent", "--agent", "claude", "--name", "helper", cwd=self.task_dir, check=False)
        self.assert_fails(result, "needs --prompt", code=2)
        self.assertFalse((self.sessions / "fix-login").exists())

    def test_agent_in_rex_is_visible_and_delete_kills_its_rex_session(self):
        self.env.update(FAKE_REX_SERVER="1", FAKE_CLAUDE_SLEEP="60")
        session_id, started = self.start("agent", "--agent", "claude", "--name", "helper", "--prompt", "hi")
        self.assertNotIn("headless", started.stderr)
        record = self.record(session_id)
        self.wait_until(lambda: "turn_started" in self.kinds(record))
        self.assertEqual(self.meta(record)["launch"]["mode"], "visible")
        self.assertNotIn("-p", self.fake_argv())
        self.assertEqual(self.fake_argv()[-2:], ["--", "hi"])
        started_event = self.events(record)[0]
        self.assertEqual((started_event["terminal"], started_event["terminal_handle"]), ("rex", "session:fake-1"))
        [new] = [call for call in self.rex_calls() if "new" in call]
        self.assertEqual(new[new.index("new") + 1], f"example/{session_id}")
        self.assertEqual(new[new.index("--cwd") + 1], str(self.task_dir / "repo"))

        self.x_env("delete", "fix-login", cwd=self.task_dir.parent.parent)
        self.assertIn(["--autostart=false", "kill", "session:fake-1"], self.rex_calls())
        self.assertEqual(self.events(record)[-1]["exit_code"], 128 + signal.SIGHUP)
        self.assertFalse((self.state / "server-started").exists())

    def test_codex_agent_in_rex_opens_the_ui_and_records_the_turn(self):
        self.env["FAKE_REX_SERVER"] = "1"
        session_id, _ = self.start("agent", "--agent", "codex", "--name", "helper", "--prompt", "hi")
        self.x_env("wait", session_id, cwd=self.task_dir)
        record = self.record(session_id)
        self.assertEqual(self.meta(record)["launch"]["mode"], "visible")
        argv = self.fake_argv()
        self.assertNotIn("exec", argv)
        self.assertEqual(argv[-2:], ["--", "hi"])
        self.assertEqual(self.kinds(record), ["started", "turn_end", "exited"])  # the title thread adds no turn
        self.assertEqual((record / "last-turn.md").read_text(), "PONG to hi")
        self.assertFalse((record / "hook-error.log").exists())

    def test_chief_sends_x_go_with_the_prompt(self):
        self.env["FAKE_REX_SERVER"] = "1"
        session_id, _ = self.start("chief", "--prompt", "fix the login bug")
        self.assertEqual(session_id, "fix-login/001-chief")
        self.x_env("wait", session_id, cwd=self.task_dir)
        meta = self.meta(self.record(session_id))
        self.assertEqual((meta["launch"]["mode"], meta["launch"]["prompt"]), ("visible", "/x:go fix the login bug"))
        argv = self.fake_argv()
        self.assertEqual(argv[-2:], ["--", "/x:go fix the login bug"])
