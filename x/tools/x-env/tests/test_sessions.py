"""Session integration tests: the `x-env` CLI with a fake `claude` and a fake
`rex` on PATH (tests/fakes). The fake claude calls the `--settings` hooks
with real payload shapes, so these tests cover the runner, the hooks, the
records, `wait`, and `delete` stopping sessions, end to end."""

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
        for name in ("claude", "rex"):  # never the real ones: a real rex would open tabs
            (self.bin / name).symlink_to(FAKES / name)
        self.state = self.root / "fake-state"
        self.state.mkdir()
        self.env.update(FAKE_CLAUDE_STATE=str(self.state), FAKE_REX_STATE=str(self.state), FAKE_REX_SERVER="0")
        self.addCleanup(self.kill_leftovers)
        self.task_dir = self.task()
        self.sessions = self.task_dir.parent.parent / "sessions"

    def kill_leftovers(self):
        pids = [self.fake_claude_pid()] + [e["pid"] for r in self.sessions.glob("*/*") for e in self.events(r)
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

    def fake_claude_argv(self):
        return json.loads((self.state / "argv.json").read_text())

    def fake_claude_pid(self):
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
        self.assertEqual(self.fake_claude_argv()[self.fake_claude_argv().index("--session-id") + 1], session)

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
        argv = self.fake_claude_argv()
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


class DeleteStopsSessionsTest(SessionTest):
    def test_delete_stops_a_running_headless_session(self):
        self.env["FAKE_CLAUDE_SLEEP"] = "60"
        session_id, _ = self.start("run", "--headless", "--agent", "claude", "--name", "probe", "--prompt", "x")
        record = self.record(session_id)
        self.wait_until(lambda: "turn_started" in self.kinds(record))
        claude_pid = self.fake_claude_pid()
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


class VisibleTest(SessionTest):
    def test_agent_runs_headless_without_a_rex_server(self):
        session_id, started = self.start("agent", "--agent", "claude", "--name", "helper", "--prompt", "hi")
        self.assertEqual(started.stderr.count("No Rex server; the session runs headless."), 1)
        self.assertEqual(self.x_env("wait", session_id, cwd=self.task_dir).returncode, 0)
        record = self.record(session_id)
        self.assertEqual(self.meta(record)["launch"]["mode"], "headless")
        self.assertIn("-p", self.fake_claude_argv())
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
        self.assertNotIn("-p", self.fake_claude_argv())
        self.assertEqual(self.fake_claude_argv()[-2:], ["--", "hi"])
        started_event = self.events(record)[0]
        self.assertEqual((started_event["terminal"], started_event["terminal_handle"]), ("rex", "session:fake-1"))
        [new] = [call for call in self.rex_calls() if "new" in call]
        self.assertEqual(new[new.index("new") + 1], f"example/{session_id}")
        self.assertEqual(new[new.index("--cwd") + 1], str(self.task_dir / "repo"))

        self.x_env("delete", "fix-login", cwd=self.task_dir.parent.parent)
        self.assertIn(["--autostart=false", "kill", "session:fake-1"], self.rex_calls())
        self.assertEqual(self.events(record)[-1]["exit_code"], 128 + signal.SIGHUP)
        self.assertFalse((self.state / "server-started").exists())

    def test_chief_sends_x_go_with_the_prompt(self):
        self.env["FAKE_REX_SERVER"] = "1"
        session_id, _ = self.start("chief", "--prompt", "fix the login bug")
        self.assertEqual(session_id, "fix-login/001-chief")
        self.x_env("wait", session_id, cwd=self.task_dir)
        meta = self.meta(self.record(session_id))
        self.assertEqual((meta["launch"]["mode"], meta["launch"]["prompt"]), ("visible", "/x:go fix the login bug"))
        argv = self.fake_claude_argv()
        self.assertEqual(argv[-2:], ["--", "/x:go fix the login bug"])
        self.assertEqual(argv[argv.index("--plugin-dir") + 1], str(Path(__file__).resolve().parents[3]))
