import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fx_sentry
from fx_context import save_response


TOOL_DIRECTORY = Path(__file__).resolve().parents[1]


class SentryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fx sentry ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.task = self.root / "task with spaces"
        self.task.mkdir()
        (self.task / "context").mkdir()

    def session(self, relative="first", agent="claude"):
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

    def test_snapshot_excludes_closed_sessions_before_reading_their_logs(self):
        active = self.session("active", "claude")
        closed = self.session("closed", "codex")
        presence = {"command_line_matches": {str(active): [{"pid": "42"}], str(closed): []}}
        with patch("fx_sentry.process_presence", return_value=presence):
            snapshot = fx_sentry.build_snapshot(self.task)
        self.assertEqual([item["directory"] for item in snapshot["sessions"]], [str(active)])

    def test_failed_process_inspection_does_not_analyze_historical_sessions(self):
        self.session()
        with patch("fx_sentry.process_presence", return_value={"error": "ps failed"}):
            with self.assertRaisesRegex(RuntimeError, "ps failed"):
                fx_sentry.build_snapshot(self.task)

    def test_snapshot_separates_verified_response_from_auxiliary_and_legacy_output(self):
        session = self.session()
        (session / "last_turn_results.md").write_text("Legacy auxiliary approval")
        presence = {"command_line_matches": {str(session): [{"pid": "42"}]}}
        with patch("fx_sentry.process_presence", return_value=presence):
            snapshot = fx_sentry.build_snapshot(self.task)["sessions"][0]
            self.assertNotIn("last_turn_results.md", snapshot["files"])
            self.assertIn("error", snapshot["latest_main_response"])
            save_response(session, "test", "main", "one", "Main review has unresolved findings")
            snapshot = fx_sentry.build_snapshot(self.task)["sessions"][0]
        self.assertEqual(snapshot["latest_main_response"]["metadata"]["origin"], "main_conversation")
        self.assertIn("unresolved findings", snapshot["latest_main_response"]["response"]["text"])

    @unittest.skipUnless(sys.platform == "linux", "Process naming fixture uses Linux prctl.")
    def test_live_process_is_included_and_disappears_after_interrupt_for_both_providers(self):
        for agent in ("claude", "codex"):
            with self.subTest(agent=agent):
                session = self.session(agent, agent)
                detector = TOOL_DIRECTORY / "agents" / f"{agent}.process"
                name, marker = subprocess.run([str(detector), str(session)], check=True,
                                               capture_output=True, text=True).stdout.splitlines()
                code = ("import ctypes,time; "
                        f"ctypes.CDLL(None).prctl(15, {name.encode()!r}, 0, 0, 0); "
                        "print('ready',flush=True); time.sleep(60)")
                process = subprocess.Popen([sys.executable, "-c", code, marker],
                                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                try:
                    self.assertEqual(process.stdout.readline().strip(), "ready")
                    snapshot = fx_sentry.build_snapshot(self.task)
                    self.assertEqual([item["directory"] for item in snapshot["sessions"]], [str(session)])
                    process.send_signal(signal.SIGINT)
                    process.wait(timeout=3)
                    self.assertEqual(fx_sentry.build_snapshot(self.task)["sessions"], [])
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    process.stdout.close()

    def test_classifications_render_one_plain_line_per_session(self):
        first = self.session("implement")
        second = self.session("groups/review/member")
        snapshot = {"task": str(self.task), "observed_at": "2026-11-03T10:00:00+00:00",
                    "sessions": [{"directory": str(first)}, {"directory": str(second)}]}
        classification = {"sessions": [
            {"session": str(second), "status": "issue", "reason": "Repeated memory failures; no progress."},
            {"session": str(first), "status": "ok", "reason": "Long healthy-session explanation."},
        ]}
        report = fx_sentry.format_report(snapshot, classification)
        self.assertEqual(report.splitlines()[1:], [
            "OK     implement", "ISSUE  groups/review/member: Repeated memory failures; no progress."])
        self.assertIn("1 issue", report.splitlines()[0])
        self.assertNotIn("Long healthy-session explanation", report)
        self.assertNotIn(str(self.task), report)

    def test_classifications_reject_missing_duplicate_and_invented_sessions(self):
        session = self.session()
        snapshot = {"task": str(self.task), "observed_at": "2026-11-03T10:00:00+00:00",
                    "sessions": [{"directory": str(session)}]}
        valid = {"session": str(session), "status": "ok", "reason": ""}
        invalid = [[], [valid, valid], [dict(valid, session="invented")],
                   [dict(valid, status="healthy")], [dict(valid, status="issue")],
                   [dict(valid, reason="x" * 161)]]
        for sessions in invalid:
            with self.subTest(sessions=sessions), self.assertRaises(ValueError):
                fx_sentry.format_report(snapshot, {"sessions": sessions})

    def test_unknown_evidence_is_not_classified_as_a_progress_failure(self):
        session = self.session()
        snapshot = {"task": str(self.task), "observed_at": "2026-11-03T10:00:00+00:00",
                    "sessions": [{"directory": str(session)}]}
        report = fx_sentry.format_report(snapshot, {"sessions": [
            {"session": str(session), "status": "unknown", "reason": "No recent event evidence."}]})
        self.assertIn("UNKNOWN first: No recent event evidence.", report)
        self.assertNotIn("ISSUE", report)

    def test_empty_task_prints_one_line_without_calling_claude(self):
        with patch("fx_sentry.shutil.which", return_value="claude"), \
             patch("fx_sentry.run_check") as check, \
             patch("builtins.print") as output:
            status = fx_sentry.main([str(self.root), str(self.task), "--headless", "--once"])
        self.assertEqual(status, 0)
        check.assert_not_called()
        output.assert_called_once()
        self.assertIn("No running agent sessions", output.call_args.args[0])

    def test_healthy_task_prints_all_good_without_explanation(self):
        session = self.session()
        snapshot = {"task": str(self.task), "observed_at": "2026-11-03T10:00:00+00:00",
                    "sessions": [{"directory": str(session)}]}
        self.assertEqual(fx_sentry.format_report(snapshot, {"sessions": [
            {"session": str(session), "status": "ok", "reason": ""}]}),
            "[10:00:00 UTC] All good\nOK     first")

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
        presence = {"command_line_matches": {str(session): [{"pid": "42"}]}}
        with patch("fx_sentry.process_presence", return_value=presence):
            snapshot = fx_sentry.build_snapshot(self.task)
        self.assertEqual(snapshot["goal"]["text"], "Make login accept valid credentials.")
        files = snapshot["sessions"][0]["files"]
        log = files["events/another-provider.log"]
        self.assertTrue(log["truncated"])
        self.assertTrue(log["text"].endswith("memory exhausted"))
        self.assertLessEqual(len(log["text"]), 8192)
        self.assertEqual(files["events/capture-error.txt"]["text"], "capture failed")
        self.assertEqual(snapshot["process_presence"], presence)

    def test_snapshot_does_not_follow_symlinked_events_or_task_context(self):
        session = self.session()
        (session / "events").symlink_to(self.root)
        with patch("fx_sentry.process_presence", return_value={"command_line_matches": {str(session): [{"pid": "42"}]}}):
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

    def test_process_presence_requires_provider_and_own_launch_marker_and_skips_zombies(self):
        session = self.session()
        marker = f"--settings {session}/claude-settings.json"
        result = subprocess.CompletedProcess([], 0, (
            f"42 1 S 00:03 claude claude {marker}\n"
            f"43 1 S 00:03 bash bash -c echo claude {marker}\n"
            f"44 1 Z 00:03 claude claude {marker}\n"
            f"45 1 S 00:03 claude claude --prompt Read {session}/findings.md\n"))
        descriptor = subprocess.CompletedProcess([], 0, f"claude\n{marker}\n")
        with patch("fx_sentry.subprocess.run", side_effect=[result, descriptor]):
            presence = fx_sentry.process_presence([session])
        self.assertEqual(presence["command_line_matches"][str(session)],
                         [{"pid": "42", "parent_pid": "1", "state": "S", "elapsed": "00:03"}])
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
        executable = self.fake_claude("import json, sys\ntext = sys.stdin.read()\nprint(json.dumps({'subtype':'success','structured_output':{'prompt':text},'is_error':False}))\n")
        prompt = 'Evidence with `commands` and $(substitution) and "quotes"'
        self.assertEqual(fx_sentry.run_check([str(executable)], prompt, self.task, 3), {"prompt": prompt})

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
        session = self.session()
        classification = {"sessions": [{"session": str(session), "status": "issue", "reason": "Repeated memory failures."}]}
        with patch("fx_sentry.shutil.which", return_value="claude"), \
             patch("fx_sentry.process_presence", return_value={"command_line_matches": {str(session): [{"pid": "42"}]}}), \
             patch("fx_sentry.run_check", return_value=classification) as check, \
             patch("fx_sentry.time.sleep") as sleep:
            status = fx_sentry.main([str(self.root), str(self.task), "--headless", "--once"])
        self.assertEqual(status, 0)
        check.assert_called_once()
        sleep.assert_not_called()
        prompt = check.call_args.args[1]
        self.assertIn("Fix login validation", prompt)
        reports = list((self.task / ".fx-sentry").glob("*/latest-report.txt"))
        self.assertEqual(reports[0].read_text().splitlines()[1], "ISSUE  first: Repeated memory failures.")
        self.assertEqual(len(fx_sentry.discover_sessions(self.task)), 1)

    def test_polling_refreshes_inventory_and_stops_after_failed_check(self):
        session = self.session()
        classification = {"sessions": [{"session": str(session), "status": "ok", "reason": ""}]}
        def add_session(_):
            self.session("second")
        with patch("fx_sentry.shutil.which", return_value="claude"), \
             patch("fx_sentry.process_presence", side_effect=lambda sessions: {"command_line_matches": {str(item): [{"pid": "42"}] for item in sessions}}), \
             patch("fx_sentry.run_check", side_effect=[classification, RuntimeError("authentication failed")]) as check, \
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
        self.assertIn("fresh evidence", instructions)
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
            session = task / "context/worker"
            session.mkdir()
            (session / "launch.txt").write_text("agent=claude\n")
            process_listing = root / "ps"
            process_listing.write_text(f"#!{sys.executable}\nprint({f'42 1 S 00:03 claude claude --settings {session}/claude-settings.json'!r})\n")
            process_listing.chmod(0o755)
            captured = root / "input.txt"
            executable = root / "claude"
            classification = {"sessions": [{"session": str(session), "status": "ok", "reason": ""}]}
            executable.write_text(f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\nPath({str(captured)!r}).write_text(sys.stdin.read())\nprint(json.dumps({{'subtype':'success','structured_output':{classification!r},'is_error':False}}))\n")
            executable.chmod(0o755)
            env["PATH"] = f"{root}:{env['PATH']}"
            result = run(tool, "agent", "sentry", "--headless", "--once", "--prompt",
                         'Check `literal` and $(literal)', cwd=task / "repo")
            self.assertIn('Check `literal` and $(literal)', captured.read_text())
            self.assertIn('"task": "' + str(task), captured.read_text())
            self.assertEqual(result.stdout.splitlines()[1], "OK     worker")
            self.assertEqual(len(result.stdout.splitlines()), 2)
            self.assertEqual(result.stderr, "")
            self.assertFalse((task / "repo/.fx-sentry").exists())
            invalid = run(tool, "agent", "sentry", "--unknown", cwd=task, check=False)
            self.assertNotEqual(invalid.returncode, 0)


if __name__ == "__main__":
    unittest.main()
