import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fx_sentry


TOOL_DIRECTORY = Path(__file__).resolve().parents[1]


class SentryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fx sentry ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.task = self.root / "task with spaces"
        self.task.mkdir()
        (self.task / "context").mkdir()

    def session(self, relative="first", agent="other-provider"):
        session = self.task / "context" / relative
        session.mkdir(parents=True)
        (session / "launch.txt").write_text(f"agent={agent}\n")
        (session / "initial_prompt.md").write_text("Fix login validation.")
        return session

    def fake_claude(self, source):
        executable = self.root / "claude"
        executable.write_text(f"#!{sys.executable}\n" + source)
        executable.chmod(0o755)
        return executable

    def test_discovers_all_providers_members_and_comparisons_without_diagnostics(self):
        sessions = [self.session(), self.session("groups/review/member", "claude"),
                    self.session("groups/review/comparisons/summary", "codex")]
        self.session("first/events/not-a-session")
        self.session("first/results/not-a-session")
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "launch.txt").write_text("private")
        (self.task / "context/alias").symlink_to(outside)
        self.assertEqual(fx_sentry.discover_sessions(self.task), sorted(sessions))
        self.session("new")
        self.assertEqual(len(fx_sentry.discover_sessions(self.task)), 4)

    def test_head_and_tail_excerpts_report_truncation_and_offsets(self):
        path = self.task / "log"
        path.write_text("begin\n" + "x" * 100 + "\nrecent")
        head = fx_sentry.read_excerpt(path, 6)
        tail = fx_sentry.read_excerpt(path, 6, tail=True)
        self.assertEqual(head["text"], "begin\n")
        self.assertEqual(tail["text"], "recent")
        self.assertTrue(head["truncated"])
        self.assertEqual(tail["offset"], path.stat().st_size - 6)

    def test_missing_and_symlinked_files_are_explicit_errors(self):
        self.assertIn("error", fx_sentry.read_excerpt(self.task / "missing", 10))
        self.assertIn("error", fx_sentry.read_excerpt(self.task, 10))
        target = self.task / "target"
        target.write_text("private")
        link = self.task / "link"
        link.symlink_to(target)
        self.assertIn("error", fx_sentry.read_excerpt(link, 10))

    def test_snapshot_includes_goal_and_arbitrary_provider_logs_with_bounded_tails(self):
        session = self.session()
        events = session / "events"
        events.mkdir()
        (events / "another-provider.log").write_text("old" * 10000 + "memory exhausted")
        (events / "capture-error.txt").write_text("capture failed")
        (self.task / "task.md").write_text("Make login accept valid credentials.")
        with patch("fx_sentry.process_presence", return_value={"error": "ps unavailable"}):
            snapshot = fx_sentry.build_snapshot(self.task)
        self.assertEqual(snapshot["goal"]["text"], "Make login accept valid credentials.")
        files = snapshot["sessions"][0]["files"]
        log = files["events/another-provider.log"]
        self.assertTrue(log["truncated"])
        self.assertTrue(log["text"].endswith("memory exhausted"))
        self.assertLessEqual(len(log["text"]), 8192)
        self.assertEqual(files["events/capture-error.txt"]["text"], "capture failed")
        self.assertEqual(snapshot["process_presence"], {"error": "ps unavailable"})

    def test_snapshot_does_not_follow_symlinked_events_or_task_context(self):
        session = self.session()
        (session / "events").symlink_to(self.root)
        snapshot = fx_sentry.build_snapshot(self.task)
        self.assertIn("error", snapshot["sessions"][0]["files"]["events"])
        (self.task / "context/first/launch.txt").unlink()
        (session / "events").unlink()
        another = self.root / "other-context"
        another.mkdir()
        context = self.task / "context"
        context.rename(self.task / "saved-context")
        context.symlink_to(another)
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            fx_sentry.discover_sessions(self.task)

    def test_missing_context_and_inventory_errors_do_not_look_like_empty_tasks(self):
        (self.task / "context").rmdir()
        with self.assertRaisesRegex(ValueError, "missing"):
            fx_sentry.discover_sessions(self.task)
        (self.task / "context").mkdir()
        def failed_walk(*args, **kwargs):
            kwargs["onerror"](PermissionError("cannot inspect sessions"))
        with patch("fx_sentry.os.walk", side_effect=failed_walk):
            with self.assertRaisesRegex(PermissionError, "cannot inspect"):
                fx_sentry.discover_sessions(self.task)

    def test_process_presence_reports_matches_without_assuming_liveness(self):
        session = self.session()
        result = subprocess.CompletedProcess([], 0, f"42 1 00:03 claude --debug-file {session}/events/log\n99 1 00:01 other\n")
        with patch("fx_sentry.subprocess.run", return_value=result):
            presence = fx_sentry.process_presence([session])
        self.assertEqual(presence["command_line_matches"][str(session)],
                         [{"pid": "42", "parent_pid": "1", "elapsed": "00:03"}])
        with patch("fx_sentry.subprocess.run", side_effect=OSError("missing ps")):
            self.assertIn("error", fx_sentry.process_presence([session]))

    def test_invalid_durations_are_rejected(self):
        self.assertEqual(fx_sentry.positive_seconds("30"), 30)
        for value in ("0", "-1", "nan", "inf"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                fx_sentry.positive_seconds(value)

    def test_command_restricts_tools_and_bounds_headless_reviews(self):
        command = fx_sentry.claude_command(Path("instructions.md"), headless=True)
        self.assertEqual(command[command.index("--model") + 1], "haiku")
        self.assertEqual(command[command.index("--tools") + 1], "Read,Glob,Grep")
        self.assertIn("--strict-mcp-config", command)
        self.assertIn("--no-session-persistence", command)
        self.assertIn("--max-turns", command)
        self.assertNotIn("--dangerously-skip-permissions", command)
        self.assertNotIn("--print", fx_sentry.claude_command(Path("instructions.md")))

    def test_run_check_uses_stdin_and_accepts_successful_report(self):
        executable = self.fake_claude("import json, sys\ntext = sys.stdin.read()\nprint(json.dumps({'subtype':'success','result':text,'is_error':False}))\n")
        prompt = 'Evidence with `commands` and $(substitution) and "quotes"'
        self.assertEqual(fx_sentry.run_check([str(executable)], prompt, self.task, 3), prompt)

    def test_failed_empty_invalid_and_budget_limited_checks_are_errors(self):
        outputs = ["not JSON", json.dumps({"subtype": "success", "result": ""}),
                   json.dumps({"subtype": "error_max_turns", "is_error": True}),
                   json.dumps({"subtype": "error_max_budget_usd"})]
        for output in outputs:
            with self.subTest(output=output):
                executable = self.fake_claude(f"print({output!r})\n")
                with self.assertRaises(RuntimeError):
                    fx_sentry.run_check([str(executable)], "Inspect", self.task, 3)
        executable = self.fake_claude("import sys\nsys.stderr.write('authentication failed')\nsys.exit(7)\n")
        with self.assertRaisesRegex(RuntimeError, "authentication failed"):
            fx_sentry.run_check([str(executable)], "Inspect", self.task, 3)

    def test_timeout_terminates_the_check_process(self):
        pid_file = self.root / "pid"
        executable = self.fake_claude(f"import os, time\nfrom pathlib import Path\nPath({str(pid_file)!r}).write_text(str(os.getpid()))\ntime.sleep(30)\n")
        with self.assertRaisesRegex(RuntimeError, "exceeded"):
            fx_sentry.run_check([str(executable)], "Inspect", self.task, 0.3)
        with self.assertRaises(ProcessLookupError):
            os.kill(int(pid_file.read_text()), 0)

    def test_once_prints_and_saves_report_without_entering_poll_loop(self):
        self.session()
        with patch("fx_sentry.shutil.which", return_value="claude"), \
             patch("fx_sentry.process_presence", return_value={}), \
             patch("fx_sentry.run_check", return_value="Attention required: memory exhausted.") as check, \
             patch("fx_sentry.time.sleep") as sleep:
            status = fx_sentry.main([str(self.root), str(self.task), "--headless", "--once"])
        self.assertEqual(status, 0)
        check.assert_called_once()
        sleep.assert_not_called()
        prompt = check.call_args.args[1]
        self.assertIn("Fix login validation", prompt)
        reports = list((self.task / ".fx-sentry").glob("*/latest-report.txt"))
        self.assertEqual(reports[0].read_text(), "Attention required: memory exhausted.")
        self.assertEqual(len(fx_sentry.discover_sessions(self.task)), 1)

    def test_polling_refreshes_inventory_and_stops_after_failed_check(self):
        self.session()
        def add_session(_):
            self.session("second")
        with patch("fx_sentry.shutil.which", return_value="claude"), \
             patch("fx_sentry.process_presence", return_value={}), \
             patch("fx_sentry.run_check", side_effect=["No issue observed.", RuntimeError("authentication failed")]) as check, \
             patch("fx_sentry.time.sleep", side_effect=add_session):
            status = fx_sentry.main([str(self.root), str(self.task), "--headless", "--interval", "30"])
        self.assertEqual(status, 1)
        self.assertEqual(check.call_count, 2)
        self.assertNotIn('"directory": "' + str(self.task / "context/second"), check.call_args_list[0].args[1])
        self.assertIn(str(self.task / "context/second"), check.call_args_list[1].args[1])

    def test_interactive_launch_has_initial_snapshot_and_live_investigation_prompt(self):
        self.session()
        with patch("fx_sentry.shutil.which", return_value="claude"), \
             patch("fx_sentry.os.chdir"), \
             patch("fx_sentry.os.execvp", side_effect=KeyboardInterrupt) as execute:
            status = fx_sentry.main([str(self.root), str(self.task)])
        self.assertEqual(status, 130)
        command = execute.call_args.args[1]
        self.assertNotIn("--print", command)
        self.assertIn("fresh evidence", command[-1])
        instructions = Path(command[command.index("--system-prompt-file") + 1]).read_text()
        self.assertIn("explicitly authorizes", instructions)
        self.assertIn("refresh", instructions)
        self.assertEqual(len(list((self.task / ".fx-sentry").glob("*/snapshot.json"))), 1)

    def test_headless_only_options_fail_before_creating_files(self):
        for options in (["--once"], ["--interval", "30"], ["--timeout", "10"]):
            with self.subTest(options=options), self.assertRaises(SystemExit):
                fx_sentry.main([str(self.root), str(self.task), *options])
        self.assertFalse((self.task / ".fx-sentry").exists())


class SentryCommandTest(unittest.TestCase):
    def test_fx_dispatches_from_worktree_and_keeps_prompt_literal(self):
        with tempfile.TemporaryDirectory(prefix="fx sentry command ") as temporary:
            root = Path(temporary)
            env = dict(os.environ, FX_ROOT=str(root / "work"),
                       GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.invalid",
                       GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="test@example.invalid")
            def run(*args, cwd=root, check=True):
                return subprocess.run([str(arg) for arg in args], cwd=cwd, env=env,
                                      capture_output=True, text=True, check=check)
            origin = root / "origin"
            run("git", "init", "-b", "main", origin)
            run("git", "-C", origin, "commit", "--allow-empty", "-m", "Initial")
            tool = TOOL_DIRECTORY / "fx"
            project = Path(run(tool, "setup", "sample", origin).stdout.strip())
            task = Path(run(tool, "task", "inspect", "--no-attach", cwd=project).stdout.strip())
            executable = root / "claude"
            executable.write_text(f"#!{sys.executable}\nimport json, sys\ntext=sys.stdin.read()\nprint(json.dumps({{'subtype':'success','result':text,'is_error':False}}))\n")
            executable.chmod(0o755)
            env["PATH"] = f"{root}:{env['PATH']}"
            result = run(tool, "agent", "sentry", "--headless", "--once", "--prompt",
                         'Check `literal` and $(literal)', cwd=task / "repo")
            self.assertIn('Check `literal` and $(literal)', result.stdout)
            self.assertIn('"task": "' + str(task), result.stdout)
            self.assertFalse((task / "repo/.fx-sentry").exists())
            invalid = run(tool, "agent", "sentry", "--unknown", cwd=task, check=False)
            self.assertNotEqual(invalid.returncode, 0)


if __name__ == "__main__":
    unittest.main()
