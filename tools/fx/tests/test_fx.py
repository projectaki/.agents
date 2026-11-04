import concurrent.futures
import json
import os
from pathlib import Path
import pty
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest


TOOL = Path(__file__).resolve().parents[1] / "fx"


class FxTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fx test ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = dict(os.environ)
        for key in list(self.env):
            if key.startswith(("GIT_", "ZELLIJ")) or key in ("BASH_ENV", "ENV", "CDPATH"):
                self.env.pop(key)
        self.env.update(
            HOME=str(self.home),
            FX_ROOT=str(self.root / 'work with "quotes" and $dollars'),
            PATH=f"{self.bin}:{os.environ['PATH']}",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="Test",
            GIT_AUTHOR_EMAIL="test@example.invalid",
            GIT_COMMITTER_NAME="Test",
            GIT_COMMITTER_EMAIL="test@example.invalid",
            CLAUDE_CODE_EFFORT_LEVEL="max",
        )
        self.origin = self.root / "origin"
        self.run_command("git", "init", "-b", "main", self.origin)
        (self.origin / "source.txt").write_text("original\n")
        self.run_command("git", "-C", self.origin, "add", ".")
        self.run_command("git", "-C", self.origin, "commit", "-m", "Initial source")
        for agent in ("claude", "codex"):
            executable = self.bin / agent
            executable.write_text(
                f"#!{sys.executable}\n"
                "import json, os, sys\n"
                "print(json.dumps({'arguments': sys.argv[1:], 'cwd': os.getcwd(), "
                "'effort_environment': os.environ.get('CLAUDE_CODE_EFFORT_LEVEL'), "
                "'record_session': os.environ.get('CODEX_TUI_RECORD_SESSION'), "
                "'session_log': os.environ.get('CODEX_TUI_SESSION_LOG_PATH'), "
                "'event_session': os.environ.get('FX_SESSION_CONTEXT_DIR')}))\n"
                "sys.exit(int(os.environ.get('FX_TEST_AGENT_EXIT', '0')))\n"
            )
            executable.chmod(0o755)
        zellij = self.bin / "zellij"
        zellij.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "print(json.dumps({'arguments': sys.argv[1:], 'cwd': os.getcwd()}))\n"
            "sys.exit(int(os.environ.get('FX_TEST_ZELLIJ_EXIT', '0')))\n"
        )
        zellij.chmod(0o755)

    def run_command(self, *arguments, cwd=None, check=True):
        return subprocess.run(
            [str(argument) for argument in arguments],
            cwd=cwd or self.root,
            env=self.env,
            text=True,
            capture_output=True,
            check=check,
        )

    def capture_codex(self, session, event):
        return subprocess.run(
            [sys.executable, str(TOOL.parent / "agents/codex_capture.py"), "hook"],
            input=json.dumps(event), text=True, capture_output=True, check=True,
            env={**self.env, "FX_SESSION_CONTEXT_DIR": str(session)},
        )

    def fx(self, *arguments, cwd=None, check=True):
        return self.run_command(TOOL, *arguments, cwd=cwd, check=check)

    def fx_with_terminal_input(self, *arguments, cwd, input_bytes):
        master, slave = pty.openpty()
        try:
            os.write(master, input_bytes)
            return subprocess.run(
                [str(TOOL), *arguments], cwd=cwd, env=self.env, stdin=slave,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10,
            )
        finally:
            os.close(slave)
            os.close(master)

    def project(self):
        return Path(self.fx("setup", "example", self.origin).stdout.strip())

    def task(self, project=None, name="fix-login"):
        project = project or self.project()
        return Path(self.fx("task", name, "--no-attach", cwd=project).stdout.strip())

    def completed_group(self, task, name="review"):
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        self.fx("agent", "group", "--name", name, "--prompt", "Review the login changes.", cwd=task)
        group = sorted((task / "context/groups").iterdir())[-1]
        manifest = json.loads((group / "run.json").read_text())
        state = {"status": "finished", "members": {}}
        for record in manifest["members"]:
            member = group / record["session"]
            event = {"hook_event_name": "Stop", "session_id": member.name, "turn_id": "one",
                     "last_assistant_message": f"Review from {member.name}: validate login input."}
            self.capture_codex(member, event)
            state["members"][member.name] = {"status": "finished", "exit_code": 0}
        (group / "run-state.json").write_text(json.dumps(state))
        return group

    def test_task_analysis_inventories_all_sessions_and_preserves_source(self):
        project = self.project()
        task = self.task(project)
        source = task / "repo/source.txt"
        source.write_text("Uncommitted change\n")
        events = task / "context/old-session/events"
        events.mkdir(parents=True)
        (events / "native.jsonl").write_text('{"error":"out of memory"}\n')
        result = self.fx("task", "analyze", "fix-login", cwd=project)
        launched = json.loads(result.stdout)
        self.assertEqual(launched["cwd"], str(task))
        session = next((task / "context/analyses").iterdir())
        inventory = json.loads((session / "evidence-inventory.json").read_text())
        self.assertIn("context/old-session/events/native.jsonl", [record["path"] for record in inventory["files"]])
        self.assertFalse(any(record["path"].startswith("context/analyses/") for record in inventory["files"]))
        self.assertEqual((session / "launch.txt").read_text().splitlines()[:2], ["agent=codex", "reasoning=high"])
        prompt = (session / "initial_prompt.md").read_text()
        self.assertIn("every review round", prompt)
        self.assertIn("earliest supported symptom", prompt)
        self.assertIn("exact unprocessed files", prompt)
        self.assertIn(str(session / "evidence-inventory.json"), prompt)
        self.assertEqual(source.read_text(), "Uncommitted change\n")

    def test_task_analysis_uses_current_task_and_supports_provider_and_reasoning(self):
        task = self.task()
        self.fx("task", "analyze", "--agent", "claude", "-r", "m", cwd=task / "repo")
        self.fx("task", "analyze", "--agent", "claude", cwd=task)
        sessions = sorted((task / "context/analyses").iterdir())
        self.assertEqual(len(sessions), 2)
        self.assertIn("agent=claude\nreasoning=medium", (sessions[0] / "launch.txt").read_text())
        self.assertNotEqual(sessions[0].name, sessions[1].name)

    def test_task_analysis_rejects_invalid_requests_before_creating_session(self):
        project = self.project()
        task = self.task(project)
        for arguments in (("missing",), ("../fix-login",), ("--no-attach",),
                          ("fix-login", "-r", "bad"), ("fix-login", "--agent", "missing"),
                          ("fix-login", "--new-tab")):
            with self.subTest(arguments=arguments):
                result = self.fx("task", "analyze", *arguments, cwd=project, check=False)
                self.assertNotEqual(result.returncode, 0)
        self.assertFalse((task / "context/analyses").exists())
        self.assertFalse((project / "tasks/missing").exists())

    def test_task_analysis_help_and_new_tab(self):
        result = self.fx("task", "analyze", "--help")
        self.assertIn("fx task analyze", result.stdout)
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        result = self.fx("task", "analyze", "--new-tab", cwd=task)
        request = json.loads(result.stdout)
        self.assertIn("new-tab", request["arguments"])
        self.assertEqual(request["cwd"], str(task))

    def test_setup_reuses_clone_and_preserves_memory_and_dirty_files(self):
        project = self.project()
        memory = project / "project_memory.md"
        source = project / "repo/main/source.txt"
        memory.write_text("Keep this decision\n")
        source.write_text("Uncommitted edit\n")
        result = self.fx("setup", "example", self.origin)
        self.assertEqual(result.stdout.strip(), str(project))
        self.assertEqual(memory.read_text(), "Keep this decision\n")
        self.assertEqual(source.read_text(), "Uncommitted edit\n")
        self.assertEqual(self.fx("setup", "example").stdout.strip(), str(project))

    def test_setup_without_repository_can_add_repository_later(self):
        project = Path(self.fx("setup", "example").stdout.strip())
        self.assertFalse((project / "repo/main").exists())
        self.assertNotEqual(self.fx("task", "fix", cwd=project, check=False).returncode, 0)
        self.assertFalse((project / "tasks/fix").exists())
        self.assertTrue((self.project() / "repo/main/.git").is_dir())

    def test_setup_rejects_different_origin(self):
        project = self.project()
        result = self.fx("setup", "example", "someone/another-repository", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("differs", result.stderr)
        origin = self.run_command("git", "-C", project / "repo/main", "remote", "get-url", "origin")
        self.assertEqual(origin.stdout.strip(), str(self.origin))

    def test_failed_clone_does_not_report_success_and_can_retry(self):
        result = self.fx("setup", "example", self.root / "missing", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertTrue((self.project() / "repo/main/.git").is_dir())

    def test_task_reuses_worktree_and_preserves_context_and_dirty_source(self):
        project = self.project()
        task = self.task(project)
        (task / "repo/source.txt").write_text("Task changes\n")
        (task / "AGENTS.md").write_text("Custom instructions\n")
        (task / "context/existing.md").write_text("Existing evidence\n")
        result = self.fx("task", "fix-login", "--no-attach", cwd=task / "repo")
        self.assertEqual(result.stdout.strip(), str(task))
        self.assertEqual((task / "repo/source.txt").read_text(), "Task changes\n")
        self.assertEqual((task / "AGENTS.md").read_text(), "Custom instructions\n")
        self.assertEqual((task / "context/existing.md").read_text(), "Existing evidence\n")
        self.assertEqual((project / "repo/main/source.txt").read_text(), "original\n")

    def test_tasks_have_separate_worktrees(self):
        project = self.project()
        first = self.task(project, "first")
        second = self.task(project, "second")
        (first / "repo/source.txt").write_text("First task changes\n")
        self.assertEqual((second / "repo/source.txt").read_text(), "original\n")
        branch = self.run_command("git", "-C", second / "repo", "branch", "--show-current")
        self.assertEqual(branch.stdout.strip(), "feature/second")

    def deletion_zellij(self, sessions="example-fix-login\n", list_exit=0, delete_exit=0):
        log = self.root / "zellij-delete.jsonl"
        executable = self.bin / "zellij"
        executable.write_text(
            f"#!{sys.executable}\n"
            "import json, sys\n"
            f"with open({str(log)!r}, 'a') as stream:\n"
            "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if sys.argv[1] == 'list-sessions':\n"
            f"    print({sessions!r}, end='', file=sys.stderr if {list_exit} else sys.stdout)\n"
            f"    sys.exit({list_exit})\n"
            f"sys.exit({delete_exit})\n"
        )
        executable.chmod(0o755)
        return log

    def test_delete_removes_task_session_and_worktree_but_keeps_branch_and_other_tasks(self):
        project = self.project()
        task = self.task(project)
        other = self.task(project, "other")
        (task / "context/findings.md").write_text("Task findings\n")
        log = self.deletion_zellij("example-fix-login-more\nexample-fix-login\nexample-other\n")
        result = self.fx("delete", "fix-login", cwd=task / "repo")
        self.assertIn("Deleted task", result.stderr)
        self.assertFalse(task.exists())
        self.assertTrue((other / "repo/source.txt").is_file())
        clone = project / "repo/main"
        worktrees = self.run_command("git", "-C", clone, "worktree", "list", "--porcelain").stdout
        self.assertNotIn(str(task / "repo"), worktrees)
        self.assertIn(str(other / "repo"), worktrees)
        self.run_command("git", "-C", clone, "show-ref", "--verify", "refs/heads/feature/fix-login")
        self.assertEqual([json.loads(line) for line in log.read_text().splitlines()], [
            ["list-sessions", "--short", "--no-formatting"],
            ["delete-session", "--force", "example-fix-login"],
        ])

    def test_delete_without_matching_session_does_not_delete_another_session(self):
        project = self.project()
        task = self.task(project)
        log = self.deletion_zellij("example-fix-login-more\n")
        self.fx("delete", "fix-login", cwd=project)
        self.assertFalse(task.exists())
        self.assertEqual(len(log.read_text().splitlines()), 1)

    def test_delete_handles_zellij_with_no_sessions(self):
        project = self.project()
        task = self.task(project)
        self.deletion_zellij("No active zellij sessions found.\n", list_exit=1)
        self.fx("delete", "fix-login", cwd=project)
        self.assertFalse(task.exists())

    def test_delete_preserves_task_on_zellij_failure(self):
        for options in ({"sessions": "Permission denied\n", "list_exit": 1}, {"delete_exit": 7}):
            with self.subTest(options=options):
                project = self.project()
                task = self.task(project)
                self.deletion_zellij(**options)
                result = self.fx("delete", "fix-login", cwd=project, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue((task / "repo/source.txt").is_file())
                self.assertIn(str(task / "repo"), self.run_command(
                    "git", "-C", project / "repo/main", "worktree", "list", "--porcelain").stdout)

    def test_delete_requires_force_for_changed_untracked_and_ignored_files(self):
        for kind in ("tracked", "untracked", "ignored"):
            with self.subTest(kind=kind):
                project = self.project()
                task = self.task(project, kind)
                source = task / "repo" / ("source.txt" if kind == "tracked" else "local.txt")
                source.write_text("Keep this work\n")
                if kind == "ignored":
                    (project / "repo/main/.git/info/exclude").write_text("local.txt\n")
                log = self.deletion_zellij("")
                result = self.fx("delete", kind, cwd=project, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("--force", result.stderr)
                self.assertFalse(log.exists())
                self.assertEqual(source.read_text(), "Keep this work\n")
                self.fx("delete", kind, "--force", cwd=project)
                self.assertFalse(task.exists())
                log.unlink()

    def test_delete_detached_worktree_requires_force(self):
        project = self.project()
        task = self.task(project)
        self.run_command("git", "-C", task / "repo", "checkout", "--detach")
        log = self.deletion_zellij()
        result = self.fx("delete", "fix-login", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("detached", result.stderr)
        self.assertFalse(log.exists())
        self.fx("delete", "fix-login", "--force", cwd=project)
        self.assertFalse(task.exists())

    def test_delete_allows_renamed_branch_and_preserves_it(self):
        project = self.project()
        task = self.task(project)
        self.run_command("git", "-C", task / "repo", "branch", "-m", "renamed-task")
        self.deletion_zellij()
        self.fx("delete", "fix-login", cwd=project)
        self.run_command("git", "-C", project / "repo/main", "show-ref", "--verify", "refs/heads/renamed-task")

    def test_delete_force_removes_worktree_during_paused_rebase(self):
        project = self.project()
        task = self.task(project)
        repo = task / "repo"
        (repo / "source.txt").write_text("Task commit\n")
        self.run_command("git", "-C", repo, "commit", "-am", "Task change")
        branch_commit = self.run_command("git", "-C", repo, "rev-parse", "HEAD").stdout.strip()
        self.env["GIT_SEQUENCE_EDITOR"] = "sed -i 's/^pick /edit /'"
        self.run_command("git", "-C", repo, "rebase", "-i", "HEAD~1")
        self.assertIn("rebase in progress", self.run_command("git", "-C", repo, "status").stdout)
        (repo / "source.txt").write_text("Uncommitted amendment\n")
        self.deletion_zellij()
        self.fx("delete", "fix-login", "--force", cwd=project)
        self.assertFalse(task.exists())
        clone = project / "repo/main"
        self.assertNotIn(str(repo), self.run_command("git", "-C", clone, "worktree", "list", "--porcelain").stdout)
        self.assertEqual(self.run_command("git", "-C", clone, "rev-parse", "feature/fix-login").stdout.strip(), branch_commit)

    def test_delete_removes_stale_worktree_registration(self):
        project = self.project()
        task = self.task(project)
        shutil.rmtree(task)
        self.deletion_zellij("")
        self.fx("delete", "fix-login", cwd=project)
        self.assertNotIn(str(task / "repo"), self.run_command(
            "git", "-C", project / "repo/main", "worktree", "list", "--porcelain").stdout)

    def test_delete_preserves_context_when_git_worktree_removal_fails(self):
        project = self.project()
        task = self.task(project)
        context = task / "context/keep.md"
        context.write_text("Keep these findings\n")
        git = shutil.which("git", path=self.env["PATH"])
        wrapper = self.bin / "git"
        wrapper.write_text(
            f"#!{sys.executable}\n"
            "import os, sys\n"
            "if sys.argv[3:5] == ['worktree', 'remove']:\n"
            "    print('Simulated removal failure', file=sys.stderr)\n"
            "    sys.exit(1)\n"
            f"os.execv({git!r}, [{git!r}, *sys.argv[1:]])\n"
        )
        wrapper.chmod(0o755)
        log = self.deletion_zellij()
        result = self.fx("delete", "fix-login", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("session is gone", result.stderr)
        self.assertEqual(context.read_text(), "Keep these findings\n")
        self.assertTrue((task / "repo/source.txt").is_file())
        self.assertEqual(json.loads(log.read_text().splitlines()[-1]),
                         ["delete-session", "--force", "example-fix-login"])
        wrapper.unlink()
        self.deletion_zellij("")
        self.fx("delete", "fix-login", cwd=project)
        self.assertFalse(task.exists())

    def test_delete_rejects_current_zellij_session_even_with_force(self):
        project = self.project()
        task = self.task(project)
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        log = self.deletion_zellij()
        result = self.fx("delete", "fix-login", "--force", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside Zellij session", result.stderr)
        self.assertTrue(task.exists())
        self.assertFalse(log.exists())

    def test_delete_rejects_locked_worktree_even_with_force(self):
        project = self.project()
        task = self.task(project)
        self.run_command("git", "-C", project / "repo/main", "worktree", "lock", task / "repo")
        log = self.deletion_zellij()
        result = self.fx("delete", "fix-login", "--force", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("locked", result.stderr)
        self.assertTrue(task.exists())
        self.assertFalse(log.exists())

    def test_delete_rejects_symlink_paths_even_with_force(self):
        for relative in ("tasks", "tasks/fix-login", "tasks/fix-login/repo"):
            with self.subTest(relative=relative):
                project = self.project()
                task = self.task(project)
                path = project / relative
                target = self.root / "outside"
                path.rename(target)
                path.symlink_to(target, target_is_directory=True)
                log = self.deletion_zellij()
                result = self.fx("delete", "fix-login", "--force", cwd=project, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(target.is_dir())
                self.assertFalse(log.exists())
                path.unlink()
                target.rename(path)

    def test_delete_rejects_worktree_from_another_repository(self):
        project = self.project()
        task = project / "tasks/fix-login"
        task.mkdir()
        self.run_command("git", "-C", self.origin, "worktree", "add", "-b", "foreign", task / "repo")
        log = self.deletion_zellij()
        result = self.fx("delete", "fix-login", "--force", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("another repository", result.stderr)
        self.assertTrue((task / "repo/source.txt").is_file())
        self.assertFalse(log.exists())

    def test_delete_retries_cleanup_without_worktree_or_task_directory(self):
        project = self.project()
        task = self.task(project)
        self.run_command("git", "-C", project / "repo/main", "worktree", "remove", task / "repo")
        self.deletion_zellij()
        self.fx("delete", "fix-login", cwd=project)
        self.assertFalse(task.exists())
        self.fx("delete", "fix-login", cwd=project)
        self.deletion_zellij("")
        result = self.fx("delete", "fix-login", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Task not found", result.stderr)

    def test_delete_rejects_invalid_arguments_before_deleting(self):
        project = self.project()
        task = self.task(project)
        log = self.deletion_zellij()
        for arguments in ((), ("../repo",), ("fix-login", "--unknown"), ("fix-login", "--force", "extra")):
            with self.subTest(arguments=arguments):
                result = self.fx("delete", *arguments, cwd=project, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(task.exists())
                self.assertFalse(log.exists())

    def test_task_copies_ignored_appsettings_with_paths_and_permissions(self):
        (self.origin / ".gitignore").write_text("appsettings*.json\n.env\nignored-dir/\n")
        self.run_command("git", "-C", self.origin, "add", ".gitignore")
        self.run_command("git", "-C", self.origin, "commit", "-m", "Ignore local settings")
        project = self.project()
        clone = project / "repo/main"
        paths = ("appsettings.json", "src/My App/appsettings.Development.json",
                 "ignored-dir/nested/appsettings.Local.json")
        for relative in paths:
            source = clone / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text('{"LocalSetting": "test-only"}\n')
            source.chmod(0o600)
        (clone / ".env").write_text("DO_NOT_COPY=1\n")
        (clone / "ignored-dir/unrelated.txt").write_text("Do not copy\n")
        task = self.task(project)
        for relative in paths:
            target = task / "repo" / relative
            self.assertTrue(target.is_file(), relative)
            self.assertEqual(target.read_bytes(), (clone / relative).read_bytes())
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertFalse((task / "repo/.env").exists())
        self.assertFalse((task / "repo/ignored-dir/unrelated.txt").exists())
        self.assertEqual(self.run_command("git", "-C", task / "repo", "status", "--porcelain").stdout, "")

    def test_task_fills_missing_settings_without_overwriting_existing_settings(self):
        project = self.project()
        clone = project / "repo/main"
        (clone / ".git/info/exclude").write_text("appsettings*.json\n")
        task = self.task(project)
        (clone / "appsettings.Local.json").write_text("main local settings\n")
        self.fx("task", "fix-login", "--no-attach", cwd=task)
        self.assertEqual((task / "repo/appsettings.Local.json").read_text(), "main local settings\n")
        (task / "repo/appsettings.Local.json").write_text("task local settings\n")
        (clone / "appsettings.Local.json").write_text("updated main settings\n")
        (clone / "appsettings.Development.json").write_text("new development settings\n")
        self.fx("task", "fix-login", "--no-attach", cwd=task)
        self.assertEqual((task / "repo/appsettings.Local.json").read_text(), "task local settings\n")
        self.assertEqual((task / "repo/appsettings.Development.json").read_text(), "new development settings\n")

    def test_settings_copy_skips_files_not_ignored_in_both_worktrees(self):
        project = self.project()
        clone = project / "repo/main"
        (clone / ".gitignore").write_text("appsettings.Local.json\n")
        (clone / "appsettings.Local.json").write_text("Ignored only in the main clone\n")
        (clone / "appsettings.Development.json").write_text("Not ignored anywhere\n")
        result = self.fx("task", "fix-login", "--no-attach", cwd=project)
        task = Path(result.stdout.strip())
        self.assertFalse((task / "repo/appsettings.Local.json").exists())
        self.assertFalse((task / "repo/appsettings.Development.json").exists())
        self.assertIn("not ignored in the task", result.stderr)

    def test_settings_copy_does_not_restore_deleted_tracked_files(self):
        project = self.project()
        clone = project / "repo/main"
        (clone / ".git/info/exclude").write_text("appsettings*.json\n")
        task = self.task(project)
        target = task / "repo/appsettings.Local.json"
        target.write_text("Tracked task settings\n")
        self.run_command("git", "-C", task / "repo", "add", "-f", "appsettings.Local.json")
        target.unlink()
        (clone / "appsettings.Local.json").write_text("Ignored clone settings\n")
        result = self.fx("task", "fix-login", "--no-attach", cwd=task)
        self.assertFalse(target.exists())
        self.assertIn("tracked or not ignored", result.stderr)

    def test_settings_copy_preserves_destination_links_and_skips_source_links(self):
        project = self.project()
        clone = project / "repo/main"
        (clone / ".git/info/exclude").write_text("appsettings*.json\n")
        task = self.task(project)
        outside = self.root / "external-settings.json"
        outside.write_text("External settings\n")
        (clone / "appsettings.Linked.json").symlink_to(outside)
        (clone / "appsettings.Local.json").write_text("Clone settings\n")
        (task / "repo/appsettings.Local.json").symlink_to(outside)
        self.fx("task", "fix-login", "--no-attach", cwd=task)
        self.assertFalse((task / "repo/appsettings.Linked.json").exists())
        self.assertTrue((task / "repo/appsettings.Local.json").is_symlink())
        self.assertEqual(outside.read_text(), "External settings\n")

    def test_settings_copy_rejects_symlink_destination_parent(self):
        project = self.project()
        clone = project / "repo/main"
        (clone / ".git/info/exclude").write_text("appsettings*.json\n")
        task = self.task(project)
        (clone / "config").mkdir()
        (clone / "config/appsettings.Local.json").write_text("Clone settings\n")
        outside = self.root / "outside"
        outside.mkdir()
        (task / "repo/config").symlink_to(outside)
        result = self.fx("task", "fix-login", "--no-attach", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symbolic link", result.stderr)
        self.assertNotIn("Task ready", result.stderr)
        self.assertEqual(list(outside.iterdir()), [])

    def test_settings_copy_failure_can_retry_without_partial_destination(self):
        project = self.project()
        clone = project / "repo/main"
        (clone / ".git/info/exclude").write_text("appsettings*.json\n")
        (clone / "appsettings.Local.json").write_text("Clone settings\n")
        fake_copy = self.bin / "cp"
        fake_copy.write_text('#!/bin/sh\nprintf partial > "$4"\nexit 23\n')
        fake_copy.chmod(0o755)
        result = self.fx("task", "fix-login", "--no-attach", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Could not copy settings", result.stderr)
        self.assertNotIn("Task ready", result.stderr)
        task = project / "tasks/fix-login"
        self.assertFalse((task / "repo/appsettings.Local.json").exists())
        self.assertEqual(list((task / "repo").glob(".fx-appsettings-*")), [])
        fake_copy.unlink()
        self.fx("task", "fix-login", "--no-attach", cwd=project)
        self.assertEqual((task / "repo/appsettings.Local.json").read_text(), "Clone settings\n")

    def test_explicit_base_checks_out_existing_local_branch_with_its_own_commits(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "switch", "-c", "feature/export")
        (clone / "source.txt").write_text("Local export changes\n")
        self.run_command("git", "-C", clone, "commit", "-am", "Export changes")
        self.run_command("git", "-C", clone, "branch", "--set-upstream-to=origin/main")
        expected = self.run_command("git", "-C", clone, "rev-parse", "HEAD").stdout
        self.run_command("git", "-C", clone, "switch", "main")
        task = Path(self.fx("task", "review", "--base", "feature/export", "--no-attach", cwd=project).stdout.strip())
        self.assertEqual(self.run_command("git", "-C", task / "repo", "branch", "--show-current").stdout.strip(), "feature/export")
        self.assertEqual(self.run_command("git", "-C", task / "repo", "rev-parse", "HEAD").stdout, expected)
        self.assertEqual((task / "repo/source.txt").read_text(), "Local export changes\n")
        self.assertEqual(self.run_command("git", "-C", task / "repo", "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(), "origin/main")
        self.assertNotEqual(self.run_command("git", "-C", clone, "show-ref", "--verify", "refs/heads/feature/review", check=False).returncode, 0)
        self.fx("task", "review", "--no-attach", cwd=task)
        self.fx("agent", "claude", "--name", "review", cwd=task)

    def test_explicit_base_overrides_an_old_task_branch_without_resetting_it(self):
        project = self.project()
        task = self.task(project, "review")
        worktree = task / "repo"
        (worktree / "source.txt").write_text("Unrelated work\n")
        self.run_command("git", "-C", worktree, "commit", "-am", "Unrelated work")
        old_head = self.run_command("git", "-C", worktree, "rev-parse", "HEAD").stdout
        self.run_command("git", "-C", self.origin, "switch", "-c", "feature/export")
        (self.origin / "source.txt").write_text("Export changes\n")
        self.run_command("git", "-C", self.origin, "commit", "-am", "Export changes")
        expected = self.run_command("git", "-C", self.origin, "rev-parse", "HEAD").stdout
        self.fx("task", "review", "--base", "origin/feature/export", "--no-attach", cwd=project)
        self.assertEqual(self.run_command("git", "-C", worktree, "branch", "--show-current").stdout.strip(), "feature/export")
        self.assertEqual(self.run_command("git", "-C", worktree, "rev-parse", "HEAD").stdout, expected)
        self.assertEqual(self.run_command("git", "-C", worktree, "rev-parse", "feature/review").stdout, old_head)
        self.assertEqual(self.run_command("git", "-C", worktree, "rev-parse", "--abbrev-ref", "feature/review@{upstream}").stdout.strip(), "origin/main")

    def test_explicit_base_ignores_an_existing_task_branch_without_a_worktree(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "branch", "feature/review")
        self.run_command("git", "-C", clone, "branch", "export")
        task = Path(self.fx("task", "review", "--base", "export", "--no-attach", cwd=project).stdout.strip())
        self.assertEqual(self.run_command("git", "-C", task / "repo", "branch", "--show-current").stdout.strip(), "export")

    def test_remote_base_creates_a_local_tracking_branch_at_the_fetched_commit(self):
        project = self.project()
        for name, prefix in (("local", ""), ("remote", "origin/")):
            with self.subTest(prefix=prefix):
                branch = f"feature/export-{name}"
                self.run_command("git", "-C", self.origin, "switch", "-c", branch, "main")
                (self.origin / "source.txt").write_text(branch + "\n")
                self.run_command("git", "-C", self.origin, "commit", "-am", "Export changes")
                expected = self.run_command("git", "-C", self.origin, "rev-parse", "HEAD").stdout
                task = Path(self.fx("task", name, "--base", prefix + branch, "--no-attach", cwd=project).stdout.strip())
                worktree = task / "repo"
                self.assertEqual(self.run_command("git", "-C", worktree, "branch", "--show-current").stdout.strip(), branch)
                self.assertEqual(self.run_command("git", "-C", worktree, "rev-parse", "HEAD").stdout, expected)
                self.assertEqual(self.run_command("git", "-C", worktree, "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(), f"origin/{branch}")

    def test_explicit_remote_reuses_local_branch_without_resetting_commits_or_upstream(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "branch", "--track", "export", "origin/main")
        self.run_command("git", "-C", clone, "switch", "export")
        (clone / "source.txt").write_text("Unpushed local changes\n")
        self.run_command("git", "-C", clone, "commit", "-am", "Local export changes")
        expected = self.run_command("git", "-C", clone, "rev-parse", "HEAD").stdout
        self.run_command("git", "-C", clone, "switch", "main")
        self.run_command("git", "-C", self.origin, "branch", "export")
        task = Path(self.fx("task", "review", "--base", "origin/export", "--no-attach", cwd=project).stdout.strip())
        self.assertEqual(self.run_command("git", "-C", task / "repo", "branch", "--show-current").stdout.strip(), "export")
        self.assertEqual(self.run_command("git", "-C", task / "repo", "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(), "origin/main")
        self.assertEqual(self.run_command("git", "-C", task / "repo", "rev-parse", "HEAD").stdout, expected)

    def test_branch_checked_out_elsewhere_is_rejected(self):
        project = self.project()
        clone = project / "repo/main"
        result = self.fx("task", "review", "--base", "main", "--no-attach", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already", result.stderr)
        self.assertNotIn("Task ready", result.stderr)
        self.assertFalse((project / "tasks/review/repo").exists())
        self.assertEqual(self.run_command("git", "-C", clone, "branch", "--show-current").stdout.strip(), "main")

    def test_reopening_cannot_take_a_branch_from_another_worktree(self):
        project = self.project()
        task = self.task(project)
        worktree = task / "repo"
        result = self.fx("task", "fix-login", "--base", "main", "--no-attach", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already", result.stderr)
        self.assertEqual(self.run_command("git", "-C", worktree, "branch", "--show-current").stdout.strip(), "feature/fix-login")

    def test_switching_task_branch_rejects_uncommitted_and_untracked_files(self):
        project = self.project()
        task = self.task(project)
        worktree = task / "repo"
        self.run_command("git", "-C", worktree, "branch", "export")
        for relative in ("source.txt", "new.txt"):
            with self.subTest(relative=relative):
                source = worktree / relative
                source.write_text("Uncommitted work\n")
                result = self.fx("task", "fix-login", "--base", "export", "--no-attach", cwd=project, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("uncommitted", result.stderr)
                self.assertEqual(source.read_text(), "Uncommitted work\n")
                self.assertEqual(self.run_command("git", "-C", worktree, "branch", "--show-current").stdout.strip(), "feature/fix-login")
                if relative == "source.txt":
                    self.run_command("git", "-C", worktree, "restore", "source.txt")
                else:
                    source.unlink()

    def test_switching_preserves_ignored_files_that_the_target_branch_tracks(self):
        project = self.project()
        task = self.task(project)
        clone = project / "repo/main"
        (clone / "settings.json").write_text("Tracked target settings\n")
        self.run_command("git", "-C", clone, "add", "settings.json")
        self.run_command("git", "-C", clone, "commit", "-m", "Track settings")
        self.run_command("git", "-C", clone, "branch", "export")
        self.run_command("git", "-C", task / "repo", "config", "core.excludesFile", str(self.root / "ignore"))
        (self.root / "ignore").write_text("settings.json\n")
        settings = task / "repo/settings.json"
        settings.write_text("Private settings\n")
        result = self.fx("task", "fix-login", "--base", "export", "--no-attach", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(settings.read_text(), "Private settings\n")

    def test_reopening_the_same_branch_preserves_dirty_files_and_works_offline(self):
        project = self.project()
        task = self.task(project)
        clone = project / "repo/main"
        (task / "repo/source.txt").write_text("Preserved local work\n")
        self.run_command("git", "-C", clone, "remote", "set-url", "origin", self.root / "missing-remote")
        for options in ((), ("--base", "feature/fix-login")):
            self.fx("task", "fix-login", *options, "--no-attach", cwd=project)
            self.assertEqual((task / "repo/source.txt").read_text(), "Preserved local work\n")

    def test_task_reattaches_existing_branch(self):
        project = self.project()
        self.run_command("git", "-C", project / "repo/main", "branch", "fix-login")
        self.assertTrue((self.task(project) / "repo/.git").is_file())

    def test_task_reattaches_legacy_branch_and_keeps_its_upstream(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "branch", "--track", "codex/fix-login", "origin/main")
        task = self.task(project)
        self.assertEqual(self.run_command("git", "-C", task / "repo", "branch", "--show-current").stdout.strip(), "codex/fix-login")
        self.assertEqual(self.run_command("git", "-C", task / "repo", "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(), "origin/main")

    def test_missing_base_is_checked_out_from_latest_default_without_changing_main(self):
        project = self.project()
        clone = project / "repo/main"
        (clone / "source.txt").write_text("Local work\n")
        (self.origin / "source.txt").write_text("Latest default\n")
        self.run_command("git", "-C", self.origin, "commit", "-am", "Update default")
        expected = self.run_command("git", "-C", self.origin, "rev-parse", "HEAD").stdout
        task = Path(self.fx("task", "review", "--base", "release/new", "--no-attach", cwd=project).stdout.strip())
        self.assertEqual(self.run_command("git", "-C", task / "repo", "branch", "--show-current").stdout.strip(), "release/new")
        self.assertEqual(self.run_command("git", "-C", task / "repo", "rev-parse", "HEAD").stdout, expected)
        self.assertNotEqual(self.run_command("git", "-C", task / "repo", "rev-parse", "@{upstream}", check=False).returncode, 0)
        self.assertEqual((clone / "source.txt").read_text(), "Local work\n")
        self.assertEqual(self.run_command("git", "-C", clone, "branch", "--show-current").stdout.strip(), "main")

    def test_missing_remote_base_is_not_created_as_local_branch(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "remote", "add", "team/upstream", self.origin)
        for base in ("origin/missing", "team/upstream/missing"):
            with self.subTest(base=base):
                result = self.fx("task", "review", "--base", base, "--no-attach", cwd=project, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Remote base branch not found", result.stderr)
                self.assertNotEqual(self.run_command("git", "-C", clone, "show-ref", "--verify", f"refs/heads/{base}", check=False).returncode, 0)
        self.assertFalse((project / "tasks/review/repo").exists())

    def test_fetch_failure_creates_no_branch_or_worktree(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "remote", "set-url", "origin", self.root / "missing-remote")
        for base in ("new-base", "origin/export"):
            with self.subTest(base=base):
                result = self.fx("task", "review", "--base", base, "--no-attach", cwd=project, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Could not fetch origin", result.stderr)
                self.assertFalse((project / "tasks/review/repo").exists())
                self.assertNotEqual(self.run_command("git", "-C", clone, "show-ref", "--verify", "refs/heads/new-base", check=False).returncode, 0)

    def test_new_task_uses_fetched_default_instead_of_current_checkout(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "switch", "-c", "unrelated")
        (clone / "source.txt").write_text("Unrelated branch change\n")
        self.run_command("git", "-C", clone, "commit", "-am", "Unrelated change")
        (self.origin / "source.txt").write_text("Latest default\n")
        self.run_command("git", "-C", self.origin, "commit", "-am", "Default change")
        task = self.task(project)
        self.assertEqual((task / "repo/source.txt").read_text(), "Latest default\n")
        self.assertEqual((clone / "source.txt").read_text(), "Unrelated branch change\n")
        self.assertEqual(self.run_command("git", "-C", task / "repo", "branch", "--show-current").stdout.strip(), "feature/fix-login")
        self.assertEqual(self.run_command("git", "-C", task / "repo", "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(), "origin/main")

    def test_default_branch_discovery_supports_non_main_names(self):
        self.run_command("git", "-C", self.origin, "branch", "-m", "trunk")
        project = self.project()
        self.run_command("git", "-C", project / "repo/main", "remote", "set-head", "origin", "--delete")
        task = self.task(project)
        self.assertEqual(self.run_command("git", "-C", task / "repo", "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(), "origin/trunk")

    def test_explicit_remote_base_supports_remote_names_with_slashes(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "remote", "set-url", "origin", self.root / "missing-remote")
        self.run_command("git", "-C", clone, "remote", "add", "team/upstream", self.origin)
        self.run_command("git", "-C", self.origin, "switch", "-c", "feature/export")
        (self.origin / "source.txt").write_text("Selected remote update\n")
        self.run_command("git", "-C", self.origin, "commit", "-am", "Update selected remote")
        task = Path(self.fx("task", "review", "--base", "team/upstream/feature/export", "--no-attach", cwd=project).stdout.strip())
        self.assertEqual((task / "repo/source.txt").read_text(), "Selected remote update\n")
        self.assertEqual(self.run_command("git", "-C", task / "repo", "branch", "--show-current").stdout.strip(), "feature/export")
        self.assertEqual(self.run_command("git", "-C", task / "repo", "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(), "team/upstream/feature/export")

    def test_invalid_base_does_not_create_a_task_branch(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "tag", "release-tag")
        commit = self.run_command("git", "-C", clone, "rev-parse", "HEAD").stdout.strip()
        for base in ("origin/missing", "bad..name", "release-tag", commit):
            with self.subTest(base=base):
                result = self.fx("task", "review", "--base", base, "--no-attach", cwd=project, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((project / "tasks/review/repo").exists())

    def test_default_fetch_failure_creates_no_branch_or_worktree(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "remote", "set-url", "origin", self.root / "missing-remote")
        result = self.fx("task", "review", "--no-attach", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Could not fetch origin", result.stderr)
        self.assertFalse((project / "tasks/review/repo").exists())
        self.assertNotEqual(self.run_command("git", "-C", clone, "show-ref", "--verify", "refs/heads/feature/review", check=False).returncode, 0)

    def test_existing_local_branch_works_with_a_missing_upstream(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "branch", "--track", "export", "origin/main")
        self.run_command("git", "-C", clone, "config", "branch.export.merge", "refs/heads/missing")
        self.run_command("git", "-C", clone, "remote", "set-url", "origin", self.root / "missing-remote")
        task = Path(self.fx("task", "review", "--base", "export", "--no-attach", cwd=project).stdout.strip())
        self.assertEqual(self.run_command("git", "-C", task / "repo", "branch", "--show-current").stdout.strip(), "export")
        self.assertEqual(self.run_command("git", "-C", clone, "config", "branch.export.merge").stdout.strip(), "refs/heads/missing")

    def test_base_option_requires_one_value(self):
        project = self.project()
        for options in (("--base",), ("--base", ""), ("--base", "--no-attach"), ("--base", "main", "--base", "main")):
            with self.subTest(options=options):
                result = self.fx("task", "invalid-base", *options, cwd=project, check=False)
                self.assertNotEqual(result.returncode, 0)
        self.assertFalse((project / "tasks/invalid-base").exists())

    def test_shell_integration_supports_base_and_no_attach_in_either_order(self):
        for options in ("--base export --no-attach", "--no-attach --base export"):
            with self.subTest(options=options):
                result = self.run_command("bash", "-c", '''
eval "$("$1" shell-init)"
fx setup example "$2" || exit
shift 2
fx task fix-login "$@" || exit
pwd -P
''', "test", TOOL, self.origin, *options.split())
                expected = Path(self.env["FX_ROOT"]) / "example/tasks/fix-login"
                self.assertEqual(result.stdout.strip(), str(expected))

    def test_task_rejects_foreign_worktree(self):
        project = self.project()
        task = project / "tasks/fix-login"
        task.mkdir()
        self.run_command("git", "-C", self.origin, "worktree", "add", "-b", "foreign", task / "repo")
        result = self.fx("task", "fix-login", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("another repository", result.stderr)

    def test_task_does_not_reset_a_switched_branch(self):
        task = self.task()
        self.run_command("git", "-C", task / "repo", "switch", "-c", "manual-branch")
        self.fx("task", "fix-login", "--no-attach", cwd=task)
        branch = self.run_command("git", "-C", task / "repo", "branch", "--show-current")
        self.assertEqual(branch.stdout.strip(), "manual-branch")

    def test_managed_directories_cannot_be_symlinks(self):
        project = self.project()
        outside = self.root / "outside"
        outside.mkdir()
        (project / "tasks/redirect").symlink_to(outside, target_is_directory=True)
        result = self.fx("task", "redirect", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_names_cannot_escape_the_project(self):
        for name in ("../escape", "a/b", "-option", "", "with spaces", "a;echo", "a\nline"):
            with self.subTest(name=name):
                result = self.fx("setup", name, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Names must", result.stderr)
        self.assertFalse(Path(self.env["FX_ROOT"]).exists())

    def test_reasoning_mapping(self):
        for short, long in (("l", "low"), ("m", "medium"), ("h", "high")):
            with self.subTest(reasoning=short):
                result = self.run_command(
                    "bash", "-c", 'source "$1"; reasoning_level "$2"', "test", TOOL, short
                )
                self.assertEqual(result.stdout.strip(), long)

    def test_repository_identity_matches_github_transports(self):
        for repository in (
            "owner/repo", "owner/repo.git", "https://github.com/owner/repo.git",
            "git@github.com:owner/repo.git", "ssh://git@github.com/owner/repo.git",
        ):
            with self.subTest(repository=repository):
                result = self.run_command(
                    "bash", "-c", 'source "$1"; repository_identity "$2"', "test", TOOL, repository
                )
                self.assertEqual(result.stdout.strip(), "owner/repo")

    def test_both_agents_receive_models_reasoning_and_no_assignment(self):
        task = self.task()
        project = task.parent.parent
        for agent in ("claude", "codex"):
            for flag, level in ((None, "medium"), ("l", "low"), ("m", "medium"), ("h", "high")):
                with self.subTest(agent=agent, reasoning=flag):
                    before = set((task / "context").iterdir())
                    extra = [] if flag is None else ["-r", flag]
                    result = self.fx("agent", agent, "--name", "review", *extra, cwd=task / "repo")
                    captured = json.loads(result.stdout)
                    created = set((task / "context").iterdir()) - before
                    self.assertEqual(len(created), 1)
                    session = created.pop()
                    instructions = (session / "instructions.md").read_text()
                    self.assertFalse((session / "initial_prompt.md").exists())
                    self.assertIn(str(session / "findings.md"), instructions)
                    self.assertIn(str(session / "last_turn_results.md"), instructions)
                    self.assertIn("Start with last_turn_results.md", instructions)
                    self.assertIn("Do not read or search any session's events/", instructions)
                    self.assertIn(str(project / "project_memory.md"), instructions)
                    self.assertIn("Wait for my interactive assignment", instructions)
                    self.assertEqual(captured["cwd"], str(task))
                    if agent == "claude":
                        self.assertEqual(captured["arguments"], [
                            "--model", "claude-opus-5-5", "--effort", level,
                            "--append-system-prompt-file", str(session / "instructions.md"),
                            "--add-dir", str(project / "project_context"),
                            "--settings", str(session / "claude-settings.json"),
                            "--debug-file", str(session / "events/claude-debug.log"),
                            "--permission-mode", "auto",
                        ])
                        self.assertIsNone(captured["effort_environment"])
                    else:
                        arguments = captured["arguments"]
                        self.assertEqual(arguments[:6], [
                            "--cd", str(task), "--model", "gpt-6.1-sol", "-c",
                            f'model_reasoning_effort="{level}"',
                        ])
                        self.assertEqual(arguments[6], "-c")
                        key, value = arguments[7].split("=", 1)
                        self.assertEqual(key, "developer_instructions")
                        self.assertEqual(json.loads(value), instructions.rstrip("\n"))
                        self.assertEqual(arguments[8:11], ["--add-dir", str(project / "project_context"), "-c"])
                        self.assertTrue(arguments[11].startswith("notify="))
                        self.assertIn("--no-daemon", arguments)
                        self.assertNotIn("--dangerously-bypass-hook-trust", arguments)
                        self.assertTrue(any(arg.startswith("hooks.PreToolUse=") for arg in arguments))
                        self.assertEqual(captured["record_session"], "1")
                        self.assertEqual(captured["session_log"], str(session / "events/codex-session.jsonl"))
                        self.assertEqual(captured["event_session"], str(session))

    def test_agents_receive_exact_initial_prompt_without_shell_evaluation(self):
        task = self.task()
        prompts = (
            'Review "login" and report findings.\nKeep the \'source\' unchanged.\n',
            'Inspect $(touch should-not-exist) and `touch also-should-not-exist` literally.',
            '--help',
            'review',
        )
        for agent in ("claude", "codex"):
            for prompt in prompts:
                with self.subTest(agent=agent, prompt=prompt):
                    before = set((task / "context").iterdir())
                    captured = json.loads(self.fx("agent", agent, "--name", "review", "--prompt", prompt, cwd=task).stdout)
                    self.assertEqual(captured["arguments"][-2:], ["--", prompt])
                    created = set((task / "context").iterdir()) - before
                    self.assertEqual(len(created), 1)
                    session = created.pop()
                    self.assertEqual((session / "initial_prompt.md").read_text(), prompt)
                    instructions = (session / "instructions.md").read_text()
                    self.assertNotIn("Wait for my interactive assignment", instructions)
                    self.assertIn("Use the initial user prompt as the assignment", instructions)
                    self.assertFalse((task / "should-not-exist").exists())
                    self.assertFalse((task / "also-should-not-exist").exists())

    def test_prompt_and_reasoning_flags_work_in_either_order(self):
        task = self.task()
        for agent in ("claude", "codex"):
            for options in (("-r", "h", "--prompt", "Investigate login"), ("--prompt", "Investigate login", "-r", "h")):
                with self.subTest(agent=agent, options=options):
                    captured = json.loads(self.fx("agent", agent, "--name", "review", *options, cwd=task).stdout)
                    arguments = captured["arguments"]
                    self.assertEqual(arguments[-2:], ["--", "Investigate login"])
                    if agent == "claude":
                        self.assertEqual(arguments[arguments.index("--effort") + 1], "high")
                    else:
                        self.assertIn('model_reasoning_effort="high"', arguments)

    def test_new_tab_runs_each_adapter_with_prompt_and_reasoning(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        prompt = 'Review "login".\nTreat $(touch should-not-exist) as literal text.'
        for agent in ("claude", "codex"):
            with self.subTest(agent=agent):
                before = set((task / "context").iterdir())
                result = self.fx("agent", agent, "--name", "review", "--new-tab", "--prompt", prompt, "-r", "h", cwd=task / "repo")
                captured = json.loads(result.stdout)
                arguments = captured["arguments"]
                self.assertEqual(arguments[:11], [
                    "--session", "example-fix-login", "action", "new-tab",
                    "--name", Path(arguments[15]).name, "--cwd", str(task), "--layout", str(TOOL.parent / "templates/agent-tab.kdl"), "--",
                ])
                self.assertEqual(captured["cwd"], str(task))
                self.assertEqual(arguments[11], str(TOOL.parent / "agents" / agent))
                session, = set((task / "context").iterdir()) - before
                self.assertEqual(arguments[12:], ["launch", str(task.parent.parent), str(task), str(session), "high", prompt])
                launched = json.loads(self.run_command(*arguments[11:], cwd=task).stdout)
                self.assertEqual(launched["arguments"][-2:], ["--", prompt])
                self.assertEqual(launched["cwd"], str(task))
                self.assertEqual(len(set((task / "context").iterdir()) - before), 1)
                self.assertFalse((task / "should-not-exist").exists())

    def test_new_tab_without_prompt_keeps_interactive_start(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        captured = json.loads(self.fx("agent", "codex", "--name", "review", "-r", "l", "--new-tab", cwd=task).stdout)
        arguments = captured["arguments"]
        self.assertEqual(arguments[-1], "low")
        session, = (task / "context").iterdir()
        self.assertFalse((session / "initial_prompt.md").exists())
        launched = json.loads(self.run_command(*arguments[11:], cwd=task).stdout)
        self.assertNotIn("--", launched["arguments"])

    def test_new_tab_accepts_custom_name_in_either_flag_order(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        for agent in ("claude", "codex"):
            for options in (("--new-tab", "--name", "review"), ("--name", "code-review", "--new-tab")):
                with self.subTest(agent=agent, options=options):
                    captured = json.loads(self.fx("agent", agent, *options, "-r", "h", "--prompt", "Review changes", cwd=task).stdout)
                    arguments = captured["arguments"]
                    self.assertEqual(arguments[arguments.index("--name") + 1], Path(arguments[15]).name)
                    self.assertIn("-" + options[options.index("--name") + 1] + "-", Path(arguments[15]).name)
                    self.assertEqual(arguments[-2:], ["high", "Review changes"])
                    self.assertEqual(arguments[11], str(TOOL.parent / "agents" / agent))

    def test_individual_agents_use_automatic_permissions(self):
        task = self.task()
        for agent in ('claude', 'codex'):
            with self.subTest(agent=agent):
                result = self.fx('agent', agent, '--name', 'review', cwd=task)
                arguments = json.loads(result.stdout)['arguments']
                if agent == 'claude':
                    self.assertEqual(arguments[arguments.index('--permission-mode') + 1], 'auto')
                    self.assertNotIn('--allowedTools', arguments)
                else:
                    self.assertIn('--dangerously-bypass-approvals-and-sandbox', arguments)

    def test_session_name_works_without_new_tab(self):
        task = self.task()
        self.fx("agent", "codex", "--name", "review", cwd=task)
        session, = (task / "context").iterdir()
        self.assertEqual(session.name, "000001-review-gpt-6.1-sol")
        self.assertTrue((session / "instructions.md").is_file())

    def test_session_numbers_increase_across_names_and_models(self):
        task = self.task()
        for agent, name in (("codex", "investigate"), ("claude", "implement"), ("codex", "investigate")):
            self.fx("agent", agent, "--name", name, cwd=task)
        self.assertEqual(sorted(path.name for path in (task / "context").iterdir()), [
            "000001-investigate-gpt-6.1-sol",
            "000002-implement-claude-opus-5-5",
            "000003-investigate-gpt-6.1-sol",
        ])

    def test_numbered_session_handoff_and_default_index(self):
        task = self.task()
        self.fx("agent", "codex", "--name", "investigate", cwd=task)
        session, = (task / "context").iterdir()
        event = {"hook_event_name": "Stop", "session_id": "investigate", "turn_id": "one",
                 "last_assistant_message": "Verified investigation report."}
        self.capture_codex(session, event)
        self.fx("agent", "codex", "--name", "index", cwd=task)
        indexed = task / "context/000002-index-gpt-6.1-sol/input-context.md"
        self.assertIn(session.name, indexed.read_text())
        self.fx("agent", "codex", "--name", "implement", "--from", session, cwd=task)
        handoff = task / "context/000003-implement-gpt-6.1-sol/input-context.md"
        self.assertIn("Verified investigation report.", handoff.read_text())

    def test_name_requirement_validates_supplied_names(self):
        for name in ("review", "Login_Review-2", "2-review", "../escape", "two words", "-review"):
            with self.subTest(name=name):
                result = self.run_command(
                    "bash", "-c", 'source "$1"; require_name Session "$2"', "test", TOOL, name, check=False,
                )
                if name in ("review", "Login_Review-2", "2-review"):
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, name + "\n")
                    self.assertEqual(result.stderr, "")
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("Names must start with", result.stderr)

    def test_model_name_comes_from_adapter_and_rejects_unsafe_output(self):
        adapters = self.root / "agents"
        adapters.mkdir()
        adapter = adapters / "custom"
        adapter.write_text('#!/bin/bash\nprintf "%s\\n" "$FX_TEST_MODEL"\nexit "${FX_TEST_MODEL_EXIT:-0}"\n')
        adapter.chmod(0o755)
        for model in ("model-v2.1", "", "../model", "two words", "model\nother"):
            with self.subTest(model=model):
                self.env["FX_TEST_MODEL"] = model
                result = self.run_command(
                    "bash", "-c", 'source "$1"; tool_dir="$2"; agent_model custom',
                    "test", TOOL, self.root, check=False,
                )
                if model == "model-v2.1":
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.strip(), model)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("invalid model name", result.stderr)
        self.env.update(FX_TEST_MODEL="model-v2.1", FX_TEST_MODEL_EXIT="23")
        result = self.run_command(
            "bash", "-c", 'source "$1"; tool_dir="$2"; agent_model custom',
            "test", TOOL, self.root, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Could not read the model", result.stderr)

    def test_missing_names_fail_without_terminal_input_and_create_no_context(self):
        task = self.task()
        group = self.completed_group(task)
        before = set((task / "context").rglob("*"))
        for arguments, kind in (
            (("agent", "codex"), "Session"),
            (("agent", "group"), "Group"),
            (("agent", "group", "compare", "review"), "Comparison session"),
        ):
            with self.subTest(kind=kind):
                result = subprocess.run(
                    [str(TOOL), *arguments], cwd=task, env=self.env, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"{kind} name is required. Supply --name", result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(set((task / "context").rglob("*")), before)
        self.assertFalse((group / "comparisons").exists())

    def test_session_name_prompt_retries_invalid_input_and_names_directory_and_tab(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        result = self.fx_with_terminal_input(
            "agent", "codex", "--new-tab", cwd=task,
            input_bytes=b"\n../escape\ntwo words\nlogin-review\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr.count("Session name: "), 4)
        session, = (task / "context").iterdir()
        self.assertEqual(session.name, "000001-login-review-gpt-6.1-sol")
        args = json.loads(result.stdout)["arguments"]
        self.assertEqual(args[5], session.name)
        self.assertEqual(args[15], str(session))

    def test_group_name_prompt_names_one_group_tab(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        result = self.fx_with_terminal_input("agent", "group", cwd=task, input_bytes=b"login-review\nReview login\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Group name: ", result.stderr)
        self.assertIn("Group assignment: ", result.stderr)
        group, = (task / "context/groups").iterdir()
        self.assertEqual(group.name, "000001-login-review")
        args = json.loads(result.stdout)["arguments"]
        self.assertEqual(args[5], group.name)
        self.assertEqual((group / "initial_prompt.md").read_text(), "Review login")

    def test_comparison_session_name_prompt_names_directory_and_tab(self):
        task = self.task()
        group = self.completed_group(task)
        result = self.fx_with_terminal_input(
            "agent", "group", "compare", "review", "--new-tab", cwd=task, input_bytes=b"login-summary\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Comparison session name: ", result.stderr)
        comparison, = (group / "comparisons").iterdir()
        self.assertEqual(comparison.name, "000002-login-summary-gpt-6.1-sol")
        args = json.loads(result.stdout)["arguments"]
        self.assertEqual(args[5], comparison.name)
        self.assertEqual(args[15], str(comparison))

    def test_name_prompt_end_of_input_cancels_without_creating_context(self):
        task = self.task()
        self.completed_group(task)
        before = set((task / "context").rglob("*"))
        for arguments in (("agent", "codex"), ("agent", "group"),
                          ("agent", "group", "compare", "review")):
            with self.subTest(arguments=arguments):
                result = self.fx_with_terminal_input(*arguments, cwd=task, input_bytes=b"\x04")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Launch canceled", result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(set((task / "context").rglob("*")), before)

    def test_invalid_session_names_create_no_sessions(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        for options in (
            ("--name",), ("--name", ""), ("--name", "   "),
            ("--name", "review\nnext"), ("--name", "review\x1b[2J"),
            ("--name", "../escape"), ("--name", "two words"),
            ("--name", "-r"), ("--name", "first", "--name", "second"),
        ):
            with self.subTest(options=options):
                result = self.fx("agent", "codex", "--new-tab", *options, cwd=task, check=False)
                self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list((task / "context").iterdir()), [])

    def test_new_tab_requires_a_current_zellij_session(self):
        task = self.task()
        for environment in ({}, {"ZELLIJ": "0"}, {"ZELLIJ_SESSION_NAME": "example-fix-login"}):
            with self.subTest(environment=environment):
                self.env.pop("ZELLIJ", None)
                self.env.pop("ZELLIJ_SESSION_NAME", None)
                self.env.update(environment)
                result = self.fx("agent", "claude", "--name", "review", "--new-tab", cwd=task, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("inside a Zellij session", result.stderr)
                self.assertEqual(list((task / "context").iterdir()), [])

    def test_new_tab_requires_zellij_before_creating_context(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        (self.bin / "zellij").unlink()
        self.env["PATH"] = f"{self.bin}:/usr/bin:/bin"
        if shutil.which("zellij", path=self.env["PATH"]):
            self.skipTest("Zellij is installed in the system test path")
        result = self.fx("agent", "claude", "--name", "review", "--new-tab", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Install Zellij", result.stderr)
        self.assertEqual(list((task / "context").iterdir()), [])

    def test_new_tab_failure_propagates_and_preserves_session_context(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login", FX_TEST_ZELLIJ_EXIT="23")
        result = self.fx("agent", "codex", "--name", "review", "--new-tab", "--prompt", "Review changes", cwd=task, check=False)
        self.assertEqual(result.returncode, 23)
        session, = (task / "context").iterdir()
        self.assertEqual((session / "initial_prompt.md").read_text(), "Review changes")

    def test_invalid_agent_arguments_create_no_sessions(self):
        task = self.task()
        for arguments in (
            ("claude", "-r", "ultra"), ("claude", "-r"), ("claude", "fix this"),
            ("claude", "--print"), ("missing",), ("../claude",), (),
            ("claude", "--prompt"), ("codex", "--prompt", ""),
            ("codex", "--prompt", " \n\t"),
            ("claude", "--prompt", "First", "--prompt", "Second"),
            ("codex", "--prompt", "Investigate", "-r"),
            ("codex", "-r", "l", "-r", "h"),
        ):
            with self.subTest(arguments=arguments):
                result = self.fx("agent", *arguments, cwd=task, check=False)
                self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list((task / "context").iterdir()), [])

    def test_group_defaults_share_exact_prompt_and_have_independent_context(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        prompt = 'Review "login".\nKeep $(touch should-not-exist) and `pwd` literal.\n'
        result = self.fx("agent", "group", "--name", "review", "--prompt", prompt, cwd=task / "repo")
        call = json.loads(result.stdout)
        group, = (task / "context/groups").iterdir()
        self.assertEqual(group.name, "000001-review")
        self.assertEqual((group / "initial_prompt.md").read_text(), prompt)
        self.assertEqual(call["arguments"][:11], ["--session", "example-fix-login", "action", "new-tab",
                         "--name", group.name, "--cwd", str(task), "--layout", str(TOOL.parent / "templates/agent-tab.kdl"), "--"])
        self.assertEqual(call["arguments"][11:], ["python3", str(TOOL.parent / "fx_group_run.py"), "run",
                         str(task.parent.parent), str(task), group.name])
        manifest = json.loads((group / "run.json").read_text())
        self.assertEqual([member["agent"] for member in manifest["members"]], ["claude", "codex"])
        for member in manifest["members"]:
            session = group / member["session"]
            self.assertEqual((session / "initial_prompt.md").read_text(), prompt)
            instructions = (session / "instructions.md").read_text()
            self.assertIn("This is an independent group investigation", instructions)
            self.assertIn("Do not inspect other members of this group", instructions)
            self.assertIn("Do not edit source", instructions)
            self.assertIn(str(session / "findings.md"), instructions)
            self.assertFalse((session / "tab-request.txt").exists())
        self.assertEqual((group / "tab-request.txt").read_text(), "accepted\n")
        self.assertFalse((task / "should-not-exist").exists())

    def test_group_custom_members_replace_defaults_and_override_reasoning(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        self.fx("agent", "group", "--name", "review", "--agent", "codex:l", "--agent", "claude:h",
                "--agent", "codex", "-r", "h", "--prompt", "Review", cwd=task)
        group, = (task / "context/groups").iterdir()
        members = json.loads((group / "run.json").read_text())["members"]
        self.assertEqual([member["agent"] for member in members], ["codex", "claude", "codex"])
        self.assertEqual([member["reasoning"] for member in members], ["low", "high", "high"])
        self.assertEqual(len({member["session"] for member in members}), 3)

    def test_group_default_reasoning_and_single_member(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        for options, count, reasoning in ((["-r", "l"], 2, "low"), (["--agent", "codex"], 1, "medium")):
            result = self.fx("agent", "group", "--name", "review", *options, "--prompt", "--help", cwd=task)
            group = task / "context/groups" / json.loads(result.stdout)["arguments"][-1]
            members = json.loads((group / "run.json").read_text())["members"]
            self.assertEqual(len(members), count)
            self.assertTrue(all(member["reasoning"] == reasoning for member in members))
            self.assertEqual((group / "initial_prompt.md").read_text(), "--help")

    def test_repeated_concurrent_groups_get_unique_directories_and_tabs(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.fx("agent", "group", "--name", "review", "--prompt", "Review", cwd=task), range(2)))
        groups = list((task / "context/groups").iterdir())
        self.assertEqual(len(groups), 2)
        tabs = [json.loads(line)["arguments"][5] for result in results for line in result.stdout.splitlines()]
        self.assertEqual(len(set(tabs)), 2)

    def test_invalid_group_arguments_create_no_context_or_tabs(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        for options in (
            ("--name",), ("--name", ""), ("--name", "../escape"), ("--name", "two words"),
            ("--name", "first", "--name", "second"), ("--agent",), ("--agent", ""),
            ("--agent", "codex:"), ("--agent", ":h"), ("--agent", "codex:h:l"),
            ("--agent", "codex", "--agent", "missing"), ("--agent", "../codex"),
            ("--agent", "codex:high"), ("--prompt",), ("--prompt", " \n\t"),
            ("--prompt", "one", "--prompt", "two"), ("-r",), ("-r", "x"),
            ("-r", "l", "-r", "h"), ("--unknown",),
        ):
            with self.subTest(options=options):
                result = self.fx("agent", "group", *options, cwd=task, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertEqual(list((task / "context").iterdir()), [])

    def test_group_checks_all_agent_clis_before_launching(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        (self.bin / "codex").unlink()
        self.env["PATH"] = f"{self.bin}:/usr/bin:/bin"
        if shutil.which("codex", path=self.env["PATH"]):
            self.skipTest("Codex is installed in the system test path")
        result = self.fx("agent", "group", "--name", "review", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("codex CLI is not available", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(list((task / "context").iterdir()), [])

    def test_group_requires_zellij_and_a_task(self):
        task = self.task()
        result = self.fx("agent", "group", "--name", "review", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inside a Zellij session", result.stderr)
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        result = self.fx("agent", "group", "--name", "review", cwd=task.parent.parent, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inside a task", result.stderr)
        self.assertEqual(list((task / "context").iterdir()), [])

    def test_group_tab_failure_preserves_all_context_and_starts_no_members(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login", FX_TEST_ZELLIJ_EXIT="23")
        result = self.fx("agent", "group", "--name", "review", "--prompt", "Review", cwd=task, check=False)
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        group, = (task / "context/groups").iterdir()
        self.assertEqual((group / "tab-request.txt").read_text().strip(), "failed: 23")
        state = json.loads((group / "run-state.json").read_text())
        self.assertTrue(all(member["status"] == "waiting" for member in state["members"].values()))
        self.assertIn("group retry", result.stderr)

    def test_group_rejects_symlink_context_parent(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        outside = self.root / "outside"
        outside.mkdir()
        (task / "context/groups").symlink_to(outside)
        result = self.fx("agent", "group", "--name", "review", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_parallel_launches_keep_separate_context(self):
        task = self.task()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.fx("agent", "claude", "--name", "review", cwd=task), range(4)))
        files = [json.loads(result.stdout)["arguments"][5] for result in results]
        self.assertEqual(len(set(files)), 4)
        self.assertEqual(len(list((task / "context").iterdir())), 4)
        sessions = sorted(path.name for path in (task / "context").iterdir())
        self.assertEqual(sessions, [f"{number:06d}-review-claude-opus-5-5" for number in range(1, 5)])

    def test_agent_failure_preserves_context_and_exit_status(self):
        task = self.task()
        self.env["FX_TEST_AGENT_EXIT"] = "23"
        result = self.fx("agent", "codex", "--name", "review", cwd=task, check=False)
        self.assertEqual(result.returncode, 23)
        session, = (task / "context").iterdir()
        self.assertTrue((session / "instructions.md").exists())

    def resume_claude_stub(self):
        executable = self.bin / "claude"
        executable.write_text(
            f"#!{sys.executable}\n"
            "import fcntl, json, os, subprocess, sys\n"
            "from pathlib import Path\n"
            "args = sys.argv[1:]\n"
            "if '--version' in args:\n"
            " print('Test Claude version')\n"
            " sys.exit(0)\n"
            "settings_path = Path(args[args.index('--settings') + 1])\n"
            "lock = (settings_path.parent / '.fx-agent.lock').open()\n"
            "try:\n"
            " fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
            " raise AssertionError('Agent process must hold the session lock')\n"
            "except BlockingIOError:\n"
            " pass\n"
            "settings = json.loads(settings_path.read_text())\n"
            "resuming = '--resume' in args\n"
            "identity = args[args.index('--resume') + 1] if resuming else 'original-conversation'\n"
            "def hook(name, **extra):\n"
            " event = dict(hook_event_name=name, session_id=identity, **extra)\n"
            " subprocess.run(settings['hooks'][name][0]['hooks'][0]['command'], shell=True,\n"
            "                input=json.dumps(event), text=True, capture_output=True, check=True)\n"
            "hook('SessionStart', source='resume' if resuming else 'startup')\n"
            "Path(args[args.index('--debug-file') + 1]).write_text('Resumed log' if resuming else 'Original log')\n"
            "if os.environ.get('FX_TEST_NO_FINAL'):\n"
            " sys.exit(130)\n"
            "hook('Stop', prompt_id='two' if resuming else 'one',\n"
            "     last_assistant_message='Resumed response' if resuming else 'Original response')\n"
            "print(json.dumps({'arguments': args, 'cwd': os.getcwd()}))\n"
        )

    def test_claude_resume_keeps_original_context_and_appends_events_and_responses(self):
        task = self.task()
        self.resume_claude_stub()
        self.fx("agent", "claude", "--name", "review", "-r", "h", "--prompt", "Original assignment", cwd=task)
        session, = (task / "context").iterdir()
        launch = session / "launch.txt"
        launch.write_text(launch.read_text().replace("model=claude-opus-5-5", "model=saved-claude-model"))
        (session / "findings.md").write_text("Keep these findings")
        preserved = {name: (session / name).read_bytes() for name in (
            "launch.txt", "instructions.md", "input-context.md", "initial_prompt.md", "findings.md", "claude-settings.json")}
        old_events = (session / "events/callbacks.jsonl").read_bytes()
        result = self.fx("agent", "claude", "--resume", session, cwd=task / "repo")
        args = json.loads(result.stdout)["arguments"]
        self.assertEqual(args[args.index('--resume') + 1], "original-conversation")
        self.assertEqual(args[args.index('--model') + 1], "saved-claude-model")
        self.assertEqual(args[args.index('--effort') + 1], "high")
        self.assertEqual(args[args.index('--settings') + 1], str(session / "claude-settings.json"))
        self.assertNotIn("Original assignment", args)
        self.assertEqual(list((task / "context").iterdir()), [session])
        for name, data in preserved.items():
            self.assertEqual((session / name).read_bytes(), data, name)
        self.assertTrue((session / "events/callbacks.jsonl").read_bytes().startswith(old_events))
        self.assertEqual((session / "events/claude-debug.log").read_text(), "Original log")
        self.assertEqual(len(list((session / "events").glob("claude-debug-resume-*.log"))), 1)
        self.assertEqual([path.read_text() for path in sorted((session / "results").glob("turn-*/response.md"))],
                         ["Original response", "Resumed response"])

    def test_claude_resume_after_interrupt_before_first_response(self):
        task = self.task()
        self.resume_claude_stub()
        self.env["FX_TEST_NO_FINAL"] = "1"
        result = self.fx("agent", "claude", "--name", "review", cwd=task, check=False)
        self.assertEqual(result.returncode, 130)
        session, = (task / "context").iterdir()
        self.assertFalse((session / "results").exists())
        self.env.pop("FX_TEST_NO_FINAL")
        self.fx("agent", "claude", "--resume", session.relative_to(task), cwd=task)
        self.assertEqual((session / "last_turn_results.md").read_text(), "Resumed response")

    def test_claude_resume_rejects_missing_identity_and_conflicting_options(self):
        task = self.task()
        self.fx("agent", "claude", "--name", "review", cwd=task)
        session, = (task / "context").iterdir()
        before = (session / "findings.md").read_bytes()
        for extra in ((), ("--name", "other"), ("--prompt", "new task"), ("-r", "h"), ("--from", str(session))):
            with self.subTest(extra=extra):
                result = self.fx("agent", "claude", "--resume", session, *extra, cwd=task, check=False)
                self.assertNotEqual(result.returncode, 0)
        self.assertEqual((session / "findings.md").read_bytes(), before)
        self.assertEqual(list((task / "context").iterdir()), [session])
        self.assertEqual(list((session / "events").glob("claude-debug-resume-*")), [])
        result = self.fx("agent", "codex", "--resume", session, cwd=task, check=False)
        self.assertIn("does not support resume", result.stderr)

    def test_claude_resume_new_tab_uses_resume_adapter_and_same_session(self):
        task = self.task()
        self.fx("agent", "claude", "--name", "review", cwd=task)
        session, = (task / "context").iterdir()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        result = self.fx("agent", "claude", "--resume", session, "--new-tab", cwd=task)
        args = json.loads(result.stdout)["arguments"]
        self.assertIn(str(TOOL.parent / "agents/claude.resume"), args)
        self.assertIn(str(session), args)
        self.assertEqual(list((task / "context").iterdir()), [session])

    def test_claude_final_responses_are_captured_without_agent_file_writes(self):
        task = self.task()
        executable = self.bin / "claude"
        executable.write_text(
            f"#!{sys.executable}\n"
            "import json, subprocess, sys\n"
            "from pathlib import Path\n"
            "args = sys.argv[1:]\n"
            "if '--settings' in args:\n"
            " settings = json.loads(Path(args[args.index('--settings') + 1]).read_text())\n"
            " hook = settings['hooks']['Stop'][0]['hooks'][0]\n"
            " for turn, text in [('one', 'Review: missing input validation.\\n'), ('two', 'Plan: validate before saving.\\n')]:\n"
            "  event = {'hook_event_name': 'Stop', 'session_id': 'claude-session', 'prompt_id': turn, 'last_assistant_message': text}\n"
            "  subprocess.run(hook['command'], shell=True, input=json.dumps(event), text=True, check=True)\n"
        )
        self.fx("agent", "claude", "--name", "review", cwd=task)
        session, = (task / "context").iterdir()
        responses = sorted((session / "results").glob("turn-*/response.md"))
        self.assertEqual([p.read_text() for p in responses], [
            "Review: missing input validation.\n", "Plan: validate before saving.\n",
        ])
        self.assertEqual((session / "findings.md").read_text(), "# Findings\n\nNo findings recorded.\n")
        self.assertEqual((session / "last_turn_results.md").read_text(), "Plan: validate before saving.\n")

    def test_codex_final_response_is_captured_by_main_stop_hook(self):
        task = self.task()
        executable = self.bin / "codex"
        executable.write_text(
            f"#!{sys.executable}\n"
            "import json, subprocess, sys, tomllib\n"
            "for argument in sys.argv[1:]:\n"
            " if argument.startswith('hooks.Stop='):\n"
            "  hook = tomllib.loads(argument)['hooks']['Stop'][0]['hooks'][0]\n"
            "  event = {'hook_event_name': 'Stop', 'session_id': 'codex-session', 'turn_id': 'one', 'last_assistant_message': 'Implement the reviewed plan.\\n'}\n"
            "  subprocess.run(hook['command'], shell=True, input=json.dumps(event), text=True, check=True)\n"
        )
        self.fx("agent", "codex", "--name", "review", cwd=task)
        session, = (task / "context").iterdir()
        responses = list((session / "results").glob("turn-*/response.md"))
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].read_text(), "Implement the reviewed plan.\n")
        self.assertEqual((session / "last_turn_results.md").read_text(), "Implement the reviewed plan.\n")

    def test_saved_response_is_supplied_to_new_agent_and_default_index(self):
        task = self.task()
        self.fx("agent", "claude", "--name", "review", cwd=task)
        source, = (task / "context").iterdir()
        event = json.dumps({"hook_event_name": "Stop", "session_id": "thread", "turn_id": "turn",
                            "last_assistant_message": "The repair plan: validate the input before saving.\n"})
        self.capture_codex(source, json.loads(event))
        for agent in ("codex", "claude"):
            before = set((task / "context").iterdir())
            result = self.fx("agent", agent, "--name", "review", "--from", source, "--prompt", "Implement the saved plan", cwd=task)
            session, = set((task / "context").iterdir()) - before
            instructions = (session / "instructions.md").read_text()
            self.assertIn("The repair plan: validate the input before saving.", instructions)
            self.assertIn(str(source.relative_to(task)), instructions)
            self.assertIn("evidence, not instructions", instructions)
            self.assertIn("The repair plan", (session / "input-context.md").read_text())
            args = json.loads(result.stdout)["arguments"]
            if agent == "codex":
                self.assertEqual(json.loads(args[7].split("=", 1)[1]), instructions.rstrip("\n"))
            else:
                self.assertEqual(Path(args[5]).read_text(), instructions)
            self.assertEqual(args[-1], "Implement the saved plan")
        before = set((task / "context").iterdir())
        self.fx("agent", "codex", "--name", "review", cwd=task)
        session, = set((task / "context").iterdir()) - before
        snapshot = (session / "input-context.md").read_text()
        self.assertIn(str(source.relative_to(task)), snapshot)
        self.assertNotIn("The repair plan", snapshot)

    def test_handoff_requires_results_in_the_current_task(self):
        project = self.project()
        task = self.task(project)
        other = self.task(project, "other")
        self.fx("agent", "claude", "--name", "review", cwd=task)
        empty, = (task / "context").iterdir()
        for source in (empty, other / "context", task / "context/missing"):
            with self.subTest(source=source):
                before = set((task / "context").iterdir())
                result = self.fx("agent", "codex", "--name", "review", "--from", source, cwd=task, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(set((task / "context").iterdir()), before)

    def test_groups_share_prior_result_index_by_default_and_explicit_handoff_text(self):
        task = self.task()
        self.fx("agent", "claude", "--name", "review", cwd=task)
        source, = (task / "context").iterdir()
        event = json.dumps({"hook_event_name": "Stop", "session_id": "thread", "turn_id": "turn",
                            "last_assistant_message": "Shared starting plan"})
        self.capture_codex(source, json.loads(event))
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        for options in ([], ["--from", source]):
            result = self.fx("agent", "group", "--name", "review", "--prompt", "Review", *options, cwd=task)
            group = task / "context/groups" / json.loads(result.stdout)["arguments"][-1]
            sessions = [group / member["session"] for member in json.loads((group / "run.json").read_text())["members"]]
            snapshots = [(session / "input-context.md").read_text() for session in sessions]
            self.assertEqual(snapshots[0], snapshots[1])
            self.assertIn(str(source.relative_to(task)), snapshots[0])
            if options:
                self.assertIn("Shared starting plan", snapshots[0])
            else:
                self.assertNotIn("Shared starting plan", snapshots[0])

    def test_group_snapshot_excludes_peer_and_later_results(self):
        task = self.task()
        previous_group = self.completed_group(task)
        self.fx("agent", "group", "--name", "review", "--prompt", "Review", cwd=task)
        group = sorted((task / "context/groups").iterdir())[-1]
        members = [group / member["session"] for member in json.loads((group / "run.json").read_text())["members"]]
        event = {"hook_event_name": "Stop", "session_id": "peer", "turn_id": "after", "last_assistant_message": "Late result"}
        self.capture_codex(members[0], event)
        snapshots = [(member / "input-context.md").read_text() for member in members]
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertIn(str(previous_group.relative_to(task)), snapshots[0])
        self.assertNotIn(str(members[0].relative_to(task)), snapshots[0])
        self.assertNotIn("Late result", snapshots[0])

    def batch_provider_stubs(self):
        for agent in ("claude", "codex"):
            executable = self.bin / agent
            executable.write_text(
                f"#!{sys.executable}\n" + '''import fcntl, json, os, sys, time
from pathlib import Path
args = sys.argv[1:]
if '--version' in args:
    print('test version')
    sys.exit(0)
session = Path(os.environ['FX_SESSION_CONTEXT_DIR'])
if '--print' in args:
    with (session / '.fx-agent.lock').open() as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            raise AssertionError('Batch session must hold its conversation lock')
        except BlockingIOError:
            pass
if 'exec' not in args and '--print' not in args:
    raise AssertionError('Expected batch execution')
(session / 'started').write_text('started')
manifest = json.loads((session.parent / 'run.json').read_text())
deadline = time.monotonic() + 5
while not all((session.parent / member['session'] / 'started').exists() for member in manifest['members']):
    if time.monotonic() > deadline:
        raise AssertionError('Group members did not run in parallel')
    time.sleep(0.01)
if session.name.startswith(os.environ.get('FX_TEST_FAIL_MEMBER', 'never-match')):
    print('Provider authentication failed', file=sys.stderr)
    sys.exit(23)
if os.environ.get('FX_TEST_EMPTY_RESPONSE'):
    sys.exit(0)
response = 'Review result from ' + session.name
if 'exec' in args:
    for event in ({'type':'thread.started','thread_id':session.name},
                  {'type':'item.completed','item':{'type':'agent_message','text':response}},
                  {'type':'turn.completed','usage':{}}):
        print(json.dumps(event))
else:
    print(json.dumps({'type':'result','subtype':'success','is_error':False,
                      'session_id':session.name,'result':response}))
''')

    def launch_batch_group(self, task):
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        launched = self.fx("agent", "group", "--name", "review", "--prompt", "Review changes", cwd=task)
        args = json.loads(launched.stdout)["arguments"]
        group = task / "context/groups" / args[-1]
        return group, args[args.index('--') + 1:]

    def test_group_runs_members_in_parallel_and_starts_one_interactive_synthesis(self):
        task = self.task()
        group, command = self.launch_batch_group(task)
        self.batch_provider_stubs()
        codex = self.bin / "codex"
        batch = codex.read_text()
        batch = batch.replace("session = Path(os.environ['FX_SESSION_CONTEXT_DIR'])", """if 'exec' not in args:
    print(json.dumps({'interactive': True, 'arguments': args, 'cwd': os.getcwd()}))
    sys.exit(0)
session = Path(os.environ['FX_SESSION_CONTEXT_DIR'])""")
        codex.write_text(batch)
        result = self.run_command(*command, cwd=task)
        final = json.loads(result.stdout.splitlines()[-1])
        self.assertTrue(final['interactive'])
        self.assertEqual(final['cwd'], str(task))
        self.assertNotIn('new-tab', final['arguments'])
        self.assertIn('All members finished', result.stdout)
        state = json.loads((group / 'run-state.json').read_text())
        self.assertEqual(state['status'], 'finished')
        for member in state['members']:
            self.assertEqual(state['members'][member]['status'], 'finished')
            self.assertIn('Review result', (group / member / 'last_turn_results.md').read_text())
        comparison, = (group / 'comparisons').iterdir()
        self.assertIn('synthesis', comparison.name)
        self.assertIn('1-claude', (comparison / 'input-context.md').read_text())
        self.assertIn('2-codex', (comparison / 'input-context.md').read_text())

    def test_group_failure_preserves_success_and_retry_runs_only_failed_member(self):
        task = self.task()
        group, command = self.launch_batch_group(task)
        self.batch_provider_stubs()
        self.env['FX_TEST_FAIL_MEMBER'] = '1-claude'
        result = self.run_command(*command, cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Group incomplete', result.stderr)
        self.assertFalse((group / 'comparisons').exists())
        successful = group / '2-codex-gpt-6.1-sol/last_turn_results.md'
        saved = successful.read_bytes()
        failed_log = group / '1-claude-claude-opus-5-5/runner.log'
        self.assertIn('authentication failed', failed_log.read_text())
        self.env.pop('FX_TEST_FAIL_MEMBER')
        codex = self.bin / 'codex'
        codex.write_text(f'#!{sys.executable}\nimport json, sys\nassert "exec" not in sys.argv\nprint(json.dumps({{"interactive":True}}))\n')
        retry = self.fx('agent', 'group', 'retry', group.name, cwd=task)
        self.assertTrue(json.loads(retry.stdout.splitlines()[-1])['interactive'])
        self.assertEqual(successful.read_bytes(), saved)
        self.assertTrue(failed_log.exists())
        state = json.loads((group / 'run-state.json').read_text())
        self.assertEqual(state['status'], 'finished')
        self.assertEqual(state['members']['1-claude-claude-opus-5-5']['status'], 'failed')
        self.assertEqual(state['members']['1-claude-claude-opus-5-5-retry-2']['status'], 'finished')
        comparison, = (group / 'comparisons').iterdir()
        snapshot = (comparison / 'input-context.md').read_text()
        self.assertIn('1-claude-claude-opus-5-5-retry-2/results', snapshot)

    def test_group_rejects_empty_successful_provider_output(self):
        task = self.task()
        group, command = self.launch_batch_group(task)
        self.batch_provider_stubs()
        self.env['FX_TEST_EMPTY_RESPONSE'] = '1'
        result = self.run_command(*command, cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((group / 'comparisons').exists())
        state = json.loads((group / 'run-state.json').read_text())
        self.assertTrue(all(member['status'] == 'failed' for member in state['members'].values()))

    def test_group_requires_assignment_without_creating_context(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        result = self.fx('agent', 'group', '--name', 'review', cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('assignment is required', result.stderr)
        self.assertEqual(list((task / 'context').iterdir()), [])

    def test_group_cancellation_stops_members_and_rejects_another_runner(self):
        task = self.task()
        group, command = self.launch_batch_group(task)
        for agent in ('claude', 'codex'):
            (self.bin / agent).write_text(f'#!{sys.executable}\n' + '''import os, signal, sys, time
from pathlib import Path
if '--version' in sys.argv:
    print('test version')
    sys.exit(0)
session = Path(os.environ['FX_SESSION_CONTEXT_DIR'])
signal.signal(signal.SIGTERM, signal.SIG_IGN)
(session / 'provider-pid').write_text(str(os.getpid()))
time.sleep(60)
''')
        process = subprocess.Popen(command, cwd=task, env=self.env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 10
            while len(list(group.glob('*/provider-pid'))) != 2:
                self.assertIsNone(process.poll())
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.02)
            duplicate = self.run_command(*command, cwd=task, check=False)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn('already running', duplicate.stderr)
            process.send_signal(signal.SIGTERM)
            _, errors = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 130, errors)
            state = json.loads((group / 'run-state.json').read_text())
            self.assertTrue(all(member['status'] == 'cancelled' for member in state['members'].values()))
            self.assertFalse((group / 'comparisons').exists())
            for path in group.glob('*/provider-pid'):
                result = self.run_command('ps', '-p', path.read_text(), '-o', 'stat=', check=False)
                self.assertTrue(not result.stdout.strip() or result.stdout.strip().startswith('Z'))
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
                process.communicate(timeout=10)

    def test_commands_require_the_correct_working_directory(self):
        project = self.project()
        self.assertNotEqual(self.fx("task", "fix", check=False).returncode, 0)
        self.assertNotEqual(self.fx("agent", "claude", "--name", "review", cwd=project, check=False).returncode, 0)

    def test_compare_group_uses_default_agent_and_captured_member_results(self):
        task = self.task()
        group = self.completed_group(task)
        result = self.fx("agent", "group", "compare", "review", "--name", "summary", cwd=task / "repo")
        args = json.loads(result.stdout)["arguments"]
        self.assertIn('model_reasoning_effort="medium"', args)
        self.assertIn("gpt-6.1-sol", args)
        comparison, = (group / "comparisons").iterdir()
        self.assertEqual((comparison / "source-group.txt").read_text().strip(), str(group))
        instructions = (comparison / "instructions.md").read_text()
        self.assertIn("1-claude-claude-opus-5-5/results/turn-000001/response.md", instructions)
        self.assertIn("2-codex-gpt-6.1-sol/results/turn-000001/response.md", instructions)
        self.assertIn("Review the login changes.", instructions)
        self.assertNotIn("This is an independent group investigation", instructions)
        self.assertEqual(json.loads(args[7].split("=", 1)[1]), instructions.rstrip("\n"))
        self.assertEqual((comparison / "initial_prompt.md").read_text(), args[-1])
        self.assertIn("Compare and merge", args[-1])
        self.assertIn("Do not edit repository files", args[-1])
        self.assertEqual(list((task / "context").iterdir()), [group.parent])

    def test_group_source_identity_and_prior_review_survive_comparison_after_edits(self):
        task = self.task()
        record = task / "context/review-record.md"
        record.write_text("Unresolved: ownership validation. Evidence: prior review.\n")
        group = self.completed_group(task)
        identity = json.loads((group / "source.json").read_text())
        self.assertIsNotNone(identity["content_sha256"])
        for member in group.iterdir():
            if member.is_dir() and (member / "instructions.md").exists():
                self.assertEqual(json.loads((member / "source.json").read_text()), identity)
                self.assertIn("ownership validation", (member / "input-context.md").read_text())
                self.assertIn(str(member / "review-record.md"), (member / "handoff.md").read_text())
        (task / "repo/source.txt").write_text("Correction after review")
        self.fx("agent", "group", "compare", "review", "--name", "summary", cwd=task)
        comparison, = (group / "comparisons").iterdir()
        current = json.loads((comparison / "source.json").read_text())
        self.assertEqual(identity["revision"], current["revision"])
        self.assertNotEqual(identity["content_sha256"], current["content_sha256"])
        snapshot = (comparison / "input-context.md").read_text()
        self.assertIn(identity["content_sha256"], snapshot)
        self.assertIn("ownership validation", snapshot)
        record.write_text("Fixed: ownership validation. Evidence: regression test.\n")
        self.assertIn("Unresolved: ownership validation", snapshot)

    def test_compare_can_use_claude_high_reasoning_in_new_tab(self):
        task = self.task()
        group = self.completed_group(task)
        result = self.fx("agent", "group", "compare", group.name, "--name", "summary", "--agent", "claude", "-r", "h", "--new-tab", cwd=task)
        args = json.loads(result.stdout)["arguments"]
        self.assertEqual(args[5], "000002-summary-claude-opus-5-5")
        self.assertEqual(args[11], str(TOOL.parent / "agents/claude"))
        self.assertEqual(args[-2], "high")
        comparison, = (group / "comparisons").iterdir()
        self.assertEqual(args[15], str(comparison))
        launched = json.loads(self.run_command(*args[11:], cwd=task).stdout)["arguments"]
        self.assertEqual(launched[3], "high")
        self.assertEqual(launched[-1], (comparison / "initial_prompt.md").read_text())

    def test_compare_rejects_missing_member_results_without_creating_session(self):
        task = self.task()
        group = self.completed_group(task)
        shutil.rmtree(group / "2-codex-gpt-6.1-sol/results")
        result = self.fx("agent", "group", "compare", "review", "--name", "summary", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("2-codex", result.stderr)
        self.assertFalse((group / "comparisons").exists())
        self.assertEqual(result.stdout, "")

    def test_compare_rejects_ambiguous_name_but_accepts_full_name(self):
        task = self.task()
        first = self.completed_group(task)
        second = self.completed_group(task)
        result = self.fx("agent", "group", "compare", "review", "--name", "summary", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(first.name, result.stderr)
        self.assertIn(second.name, result.stderr)
        self.assertFalse((first / "comparisons").exists())
        self.assertFalse((second / "comparisons").exists())
        self.fx("agent", "group", "compare", first.name, "--name", "summary", cwd=task)
        self.assertTrue((first / "comparisons").is_dir())

    def test_repeated_comparisons_capture_results_and_do_not_feed_previous_merges_back(self):
        task = self.task()
        group = self.completed_group(task)
        self.fx("agent", "group", "compare", "review", "--name", "summary", cwd=task)
        first, = (group / "comparisons").iterdir()
        event = {"hook_event_name": "Stop", "session_id": "comparison", "turn_id": "one",
                 "last_assistant_message": "Merged report: add validation and tests."}
        self.capture_codex(first, event)
        self.fx("agent", "group", "compare", "review", "--name", "summary", cwd=task)
        second, = set((group / "comparisons").iterdir()) - {first}
        self.assertNotIn("Merged report", (second / "input-context.md").read_text())
        result = self.fx("agent", "claude", "--name", "review", "--from", first, cwd=task)
        instructions = Path(json.loads(result.stdout)["arguments"][5]).read_text()
        self.assertIn("Merged report: add validation and tests.", instructions)
        result = self.fx("agent", "claude", "--name", "review", cwd=task)
        instructions = Path(json.loads(result.stdout)["arguments"][5]).read_text()
        self.assertIn(str(first.relative_to(task) / "results/turn-000001/response.md"), instructions)

    def test_compare_rejects_invalid_arguments(self):
        task = self.task()
        for options in ((), ("missing",), ("../escape",), ("review", "--agent"),
                        ("review", "--agent", "codex", "--agent", "claude"),
                        ("review", "-r", "x"), ("review", "-r", "l", "-r", "h"),
                        ("review", "--unknown"), ("review", "--new-tab")):
            with self.subTest(options=options):
                result = self.fx("agent", "group", "compare", *options, cwd=task, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
        self.assertEqual(list((task / "context").iterdir()), [])

    def test_compare_rejects_failed_tab_and_capture_error(self):
        task = self.task()
        group = self.completed_group(task)
        request = group / "1-claude-claude-opus-5-5/tab-request.txt"
        request.write_text("failed: 23\n")
        result = self.fx("agent", "group", "compare", "review", "--name", "summary", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not accepted", result.stderr)
        request.write_text("accepted\n")
        (group / "2-codex-gpt-6.1-sol/capture-error.txt").write_text("Capture failed")
        result = self.fx("agent", "group", "compare", "review", "--name", "summary", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Capture failed", result.stderr)
        self.assertFalse((group / "comparisons").exists())

    def test_shell_integration_changes_directory_only_after_success(self):
        shells = ["bash"]
        if shutil.which("zsh"):
            shells.append("zsh")
        for shell in shells:
            with self.subTest(shell=shell):
                result = self.run_command(shell, "-c", '''
eval "$("$1" shell-init)"
fx setup example "$2" || exit
fx task fix-login --no-attach || exit
pwd -P
fx task ../invalid >/dev/null 2>&1 && exit 1
pwd -P
''', "test", TOOL, self.origin)
                task = Path(self.env["FX_ROOT"]) / "example/tasks/fix-login"
                self.assertEqual(result.stdout.splitlines(), [str(task), str(task)])

    def test_task_creates_or_reattaches_named_session_in_task_directory(self):
        project = self.project()
        task = project / "tasks/fix-login"
        for _ in range(2):
            captured = json.loads(self.fx("task", "fix-login", cwd=project).stdout)
            self.assertEqual(captured, {
                "arguments": ["--layout-string", self.run_command(sys.executable, TOOL.parent / "fx_task.py", "layout", task).stdout.rstrip("\n"), "attach", "--create", "example-fix-login", "options", "--default-cwd", str(task)],
                "cwd": str(task),
            })
            self.assertTrue((task / "repo/.git").is_file())

    def test_task_switches_sessions_when_inside_zellij(self):
        project = self.project()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="previous-task")
        task = project / "tasks/next-task"
        captured = json.loads(self.fx("task", "next-task", cwd=project).stdout)
        self.assertEqual(captured, {
            "arguments": ["action", "switch-session", "example-next-task", "--cwd", str(task), "--layout-string", self.run_command(sys.executable, TOOL.parent / "fx_task.py", "layout", task).stdout.rstrip("\n")],
            "cwd": str(task),
        })

    def test_initial_task_terminal_reports_live_state_before_opening_the_shell(self):
        project = self.project()
        task = self.task(project)
        (task / "repo/source.txt").write_text("Uncommitted change\n")
        shell = self.bin / "task-shell"
        shell.write_text(f"#!{sys.executable}\nimport os, sys\nprint('Shell opened:', os.getcwd(), sys.argv[1:])\n")
        shell.chmod(0o755)
        self.env.update(SHELL=str(shell), ZELLIJ_SESSION_NAME="example-fix-login")
        result = self.run_command(sys.executable, TOOL.parent / "fx_task.py", "shell", task)
        self.assertIn(f"Directory: {task}", result.stdout)
        self.assertIn(f"Repository: {task / 'repo'}", result.stdout)
        self.assertIn("Zellij session: example-fix-login", result.stdout)
        self.assertIn("Initial source", result.stdout)
        self.assertIn("On branch feature/fix-login", result.stdout)
        self.assertIn("modified:   source.txt", result.stdout)
        self.assertTrue(result.stdout.rstrip().endswith(f"Shell opened: {task} ['-i']"))
        self.assertNotIn("Directory:", self.fx("task", "fix-login", "--no-attach", cwd=project).stdout)

    def test_initial_task_terminal_keeps_the_shell_available_when_git_fails(self):
        task = self.task()
        git = self.bin / "git"
        git.write_text("#!/bin/sh\nexit 23\n")
        git.chmod(0o755)
        self.env["SHELL"] = "/bin/true"
        result = self.run_command(sys.executable, TOOL.parent / "fx_task.py", "shell", task)
        self.assertIn("Could not read latest commit", result.stderr)
        self.assertIn("Could not read git status", result.stderr)

    def test_task_does_not_attach_to_itself(self):
        project = self.project()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        result = self.fx("task", "fix-login", cwd=project)
        self.assertEqual(result.stdout, "")
        self.assertIn("Already in Zellij session", result.stderr)

    def test_session_failure_preserves_task_and_exit_status(self):
        project = self.project()
        self.env["FX_TEST_ZELLIJ_EXIT"] = "23"
        result = self.fx("task", "fix-login", cwd=project, check=False)
        self.assertEqual(result.returncode, 23)
        self.assertTrue((project / "tasks/fix-login/repo/.git").is_file())

    def test_shell_integration_does_not_capture_terminal_output(self):
        result = self.run_command("bash", "-c", '''
eval "$("$1" shell-init)"
fx setup example "$2" || exit
fx task fix-login
''', "test", TOOL, self.origin)
        captured = json.loads(result.stdout)
        self.assertEqual(captured["arguments"][2:5], ["attach", "--create", "example-fix-login"])

    def test_old_shell_helper_cannot_capture_zellij_screen(self):
        project = self.project()
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        result = subprocess.run(
            ["bash", "-c", 'destination="$("$1" task fix-login)"', "test", str(TOOL)],
            cwd=project, env=self.env, stdin=slave,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source ~/.bashrc", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse((project / "tasks/fix-login").exists())

    def test_no_attach_can_return_path_to_an_interactive_shell_helper(self):
        project = self.project()
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        result = subprocess.run(
            [str(TOOL), "task", "fix-login", "--no-attach"],
            cwd=project, env=self.env, stdin=slave,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(project / "tasks/fix-login"))

    def test_interactive_task_passes_terminal_output_to_zellij(self):
        project = self.project()
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        result = subprocess.run(
            [str(TOOL), "task", "fix-login"],
            cwd=project, env=self.env, stdin=slave, stdout=slave,
            stderr=subprocess.PIPE, text=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        captured = json.loads(os.read(master, 4096).decode())
        self.assertEqual(captured["arguments"][2:5], ["attach", "--create", "example-fix-login"])

    def test_same_task_name_in_different_projects_uses_distinct_sessions(self):
        first_project = self.project()
        second_project = Path(self.fx("setup", "another-project", self.origin).stdout.strip())
        first = json.loads(self.fx("task", "fix-login", cwd=first_project).stdout)
        second = json.loads(self.fx("task", "fix-login", cwd=second_project).stdout)
        self.assertEqual(first["arguments"][4], "example-fix-login")
        self.assertEqual(second["arguments"][4], "another-project-fix-login")

    def test_same_task_name_in_another_project_switches_sessions(self):
        project = self.project()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="another-project-fix-login")
        captured = json.loads(self.fx("task", "fix-login", cwd=project).stdout)
        self.assertEqual(captured["arguments"][:3], ["action", "switch-session", "example-fix-login"])

    def test_task_rejects_unknown_options(self):
        project = self.project()
        result = self.fx("task", "fix-login", "--unknown", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((project / "tasks/fix-login").exists())


if __name__ == "__main__":
    unittest.main()
