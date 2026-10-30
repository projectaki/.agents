import concurrent.futures
import json
import os
from pathlib import Path
import pty
import shutil
import subprocess
import sys
import tempfile
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
                "'effort_environment': os.environ.get('CLAUDE_CODE_EFFORT_LEVEL')}))\n"
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

    def fx(self, *arguments, cwd=None, check=True):
        return self.run_command(TOOL, *arguments, cwd=cwd, check=check)

    def project(self):
        return Path(self.fx("setup", "example", self.origin).stdout.strip())

    def task(self, project=None, name="fix-login"):
        project = project or self.project()
        return Path(self.fx("task", name, "--no-attach", cwd=project).stdout.strip())

    def completed_group(self, task, name="review"):
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        launched = self.fx("agent", "group", "--name", name, "--prompt", "Review the login changes.", cwd=task)
        for line in launched.stdout.splitlines():
            member = Path(json.loads(line)["arguments"][13])
            event = {"type": "agent-turn-complete", "thread-id": member.name, "turn-id": "one",
                     "last-assistant-message": f"Review from {member.name}: validate login input."}
            self.run_command(sys.executable, TOOL.parent / "agents/codex_capture.py", "capture", member, json.dumps(event))
        return member.parent

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

    def test_two_tasks_can_start_from_the_same_checked_out_base_branch(self):
        project = self.project()
        clone = project / "repo/main"
        base_commit = self.run_command("git", "-C", clone, "rev-parse", "main").stdout.strip()
        for name in ("first", "second"):
            result = self.fx("task", name, "--base", "main", "--no-attach", cwd=project)
            worktree = Path(result.stdout.strip()) / "repo"
            commit = self.run_command("git", "-C", worktree, "rev-parse", "HEAD").stdout.strip()
            branch = self.run_command("git", "-C", worktree, "branch", "--show-current").stdout.strip()
            self.assertEqual(commit, base_commit)
            self.assertEqual(branch, f"feature/{name}")
            upstream = self.run_command("git", "-C", worktree, "rev-parse", "--abbrev-ref", "@{upstream}")
            self.assertEqual(upstream.stdout.strip(), "origin/main")
        branch = self.run_command("git", "-C", clone, "branch", "--show-current").stdout.strip()
        self.assertEqual(branch, "main")

    def test_task_reattaches_existing_branch(self):
        project = self.project()
        self.run_command("git", "-C", project / "repo/main", "branch", "fix-login")
        self.assertTrue((self.task(project) / "repo/.git").is_file())

    def test_task_can_fetch_and_merge_changes_from_its_remote_base(self):
        self.run_command("git", "-C", self.origin, "switch", "-c", "develop")
        project = self.project()
        task = Path(self.fx("task", "fix-login", "--base", "origin/develop", "--no-attach", cwd=project).stdout.strip())
        worktree = task / "repo"
        self.assertEqual(self.run_command("git", "-C", worktree, "branch", "--show-current").stdout.strip(), "feature/fix-login")
        self.assertEqual(self.run_command("git", "-C", worktree, "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(), "origin/develop")
        (self.origin / "source.txt").write_text("New base changes\n")
        self.run_command("git", "-C", self.origin, "commit", "-am", "Update development")
        expected = self.run_command("git", "-C", self.origin, "rev-parse", "HEAD").stdout
        self.run_command("git", "-C", worktree, "fetch")
        self.assertEqual(self.run_command("git", "-C", worktree, "rev-parse", "@{upstream}").stdout, expected)
        self.assertEqual((worktree / "source.txt").read_text(), "original\n")
        self.run_command("git", "-C", worktree, "merge", "--ff-only", "@{upstream}")
        self.assertEqual((worktree / "source.txt").read_text(), "New base changes\n")

    def test_base_upstream_resolution(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "branch", "--no-track", "local-only")
        self.run_command("git", "-C", clone, "branch", "--track", "tracked-base", "origin/main")
        self.run_command("git", "-C", clone, "branch", "--unset-upstream", "main")
        for reference, expected in (
            ("refs/remotes/origin/HEAD", "refs/remotes/origin/main"),
            ("refs/remotes/origin/main", "refs/remotes/origin/main"),
            ("refs/heads/main", "refs/remotes/origin/main"),
            ("refs/heads/tracked-base", "refs/remotes/origin/main"),
            ("refs/heads/local-only", "refs/heads/local-only"),
        ):
            with self.subTest(reference=reference):
                result = self.run_command("bash", "-c", 'source "$1"; resolve_base_upstream "$2" "$3"',
                                          "test", TOOL, clone, reference)
                self.assertEqual(result.stdout.strip(), expected)

    def test_task_inherits_the_local_bases_configured_remote_upstream(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "remote", "add", "upstream", self.origin)
        self.run_command("git", "-C", clone, "fetch", "upstream")
        self.run_command("git", "-C", clone, "branch", "--track", "local-base", "upstream/main")
        task = Path(self.fx("task", "fix-login", "--base", "local-base", "--no-attach", cwd=project).stdout.strip())
        tracked = self.run_command("git", "-C", task / "repo", "rev-parse", "--abbrev-ref", "@{upstream}")
        self.assertEqual(tracked.stdout.strip(), "upstream/main")

    def test_legacy_task_can_relink_upstream_without_renaming_or_resetting(self):
        task = self.task()
        worktree = task / "repo"
        self.run_command("git", "-C", worktree, "branch", "-m", "codex/fix-login")
        self.run_command("git", "-C", worktree, "branch", "--unset-upstream")
        (worktree / "source.txt").write_text("Task commit\n")
        self.run_command("git", "-C", worktree, "commit", "-am", "Task work")
        head = self.run_command("git", "-C", worktree, "rev-parse", "HEAD").stdout
        (worktree / "source.txt").write_text("Uncommitted task work\n")
        self.fx("task", "fix-login", "--base", "origin/main", "--no-attach", cwd=task)
        self.assertEqual(self.run_command("git", "-C", worktree, "branch", "--show-current").stdout.strip(), "codex/fix-login")
        self.assertEqual(self.run_command("git", "-C", worktree, "rev-parse", "HEAD").stdout, head)
        self.assertEqual((worktree / "source.txt").read_text(), "Uncommitted task work\n")
        self.assertEqual(self.run_command("git", "-C", worktree, "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(), "origin/main")
        self.fx("agent", "claude", cwd=task)
        self.run_command("git", "-C", worktree, "branch", "-m", "fix-login")
        self.fx("agent", "claude", cwd=task)

    def test_task_reattaches_legacy_branch_and_keeps_its_upstream(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "branch", "--track", "codex/fix-login", "origin/main")
        task = self.task(project)
        self.assertEqual(self.run_command("git", "-C", task / "repo", "branch", "--show-current").stdout.strip(), "codex/fix-login")
        self.assertEqual(self.run_command("git", "-C", task / "repo", "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(), "origin/main")

    def test_missing_configured_base_upstream_fails_before_creating_task_branch(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "config", "branch.main.merge", "refs/heads/missing")
        result = self.fx("task", "fix-login", "--base", "main", "--no-attach", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("upstream is unavailable", result.stderr)
        self.assertFalse((project / "tasks/fix-login/repo").exists())

    def test_reopening_without_base_preserves_upstream_and_invalid_base_changes_nothing(self):
        task = self.task()
        worktree = task / "repo"
        self.fx("task", "fix-login", "--no-attach", cwd=task)
        result = self.fx("task", "fix-login", "--base", "missing", "--no-attach", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.run_command("git", "-C", worktree, "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(), "origin/main")

    def test_new_task_uses_recorded_default_instead_of_current_checkout(self):
        project = self.project()
        clone = project / "repo/main"
        expected = self.run_command("git", "-C", clone, "rev-parse", "origin/main").stdout.strip()
        self.run_command("git", "-C", clone, "switch", "-c", "unrelated")
        (clone / "source.txt").write_text("Unrelated branch change\n")
        self.run_command("git", "-C", clone, "commit", "-am", "Unrelated change")
        task = self.task(project)
        actual = self.run_command("git", "-C", task / "repo", "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(actual, expected)
        self.assertEqual((task / "repo/source.txt").read_text(), "original\n")
        upstream = self.run_command("git", "-C", task / "repo", "rev-parse", "@{upstream}", check=False)
        self.assertEqual(upstream.returncode, 0)
        self.assertEqual(upstream.stdout.strip(), expected)

    def test_new_task_supports_a_default_branch_not_named_main(self):
        self.run_command("git", "-C", self.origin, "branch", "-m", "trunk")
        project = self.project()
        result = self.fx("task", "fix-login", "--no-attach", cwd=project)
        self.assertIn("refs/remotes/origin/trunk", result.stderr)
        self.assertTrue((Path(result.stdout.strip()) / "repo/.git").is_file())

    def test_explicit_base_uses_remote_upstream_even_when_local_branch_is_older(self):
        self.run_command("git", "-C", self.origin, "switch", "-c", "develop")
        (self.origin / "source.txt").write_text("Remote development\n")
        self.run_command("git", "-C", self.origin, "commit", "-am", "Development change")
        self.run_command("git", "-C", self.origin, "branch", "release")
        self.run_command("git", "-C", self.origin, "switch", "main")
        project = self.project()
        self.run_command("git", "-C", project / "repo/main", "branch", "develop", "main")
        for name, base, expected in (
            ("local", "develop", "Remote development\n"),
            ("remote", "origin/develop", "Remote development\n"),
            ("remote-fallback", "release", "Remote development\n"),
        ):
            with self.subTest(base=base):
                result = self.fx("task", name, "--base", base, "--no-attach", cwd=project)
                task = Path(result.stdout.strip())
                self.assertEqual((task / "repo/source.txt").read_text(), expected)

    def test_fetch_restores_a_missing_default_branch_reference(self):
        project = self.project()
        self.run_command("git", "-C", project / "repo/main", "remote", "set-head", "origin", "--delete")
        result = self.fx("task", "fix-login", "--no-attach", cwd=project)
        self.assertTrue((Path(result.stdout.strip()) / "repo/.git").is_file())

    def test_new_tasks_fetch_the_latest_default_base(self):
        project = self.project()
        (self.origin / "source.txt").write_text("Latest remote changes\n")
        self.run_command("git", "-C", self.origin, "commit", "-am", "Remote change")
        task = self.task(project)
        self.assertEqual((task / "repo/source.txt").read_text(), "Latest remote changes\n")
        self.assertEqual((project / "repo/main/source.txt").read_text(), "original\n")

    def test_new_task_discovers_a_base_created_after_cloning(self):
        project = self.project()
        self.run_command("git", "-C", self.origin, "switch", "-c", "release/new")
        (self.origin / "source.txt").write_text("New remote base\n")
        self.run_command("git", "-C", self.origin, "commit", "-am", "New release branch")
        task = Path(self.fx("task", "new-release", "--base", "origin/release/new", "--no-attach", cwd=project).stdout.strip())
        self.assertEqual((task / "repo/source.txt").read_text(), "New remote base\n")
        self.assertEqual(self.run_command("git", "-C", task / "repo", "branch", "--show-current").stdout.strip(), "feature/new-release")

    def test_new_task_fetch_failure_does_not_use_a_stale_base(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "remote", "set-url", "origin", self.root / "missing-remote")
        result = self.fx("task", "fresh-task", "--base", "main", "--no-attach", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Could not fetch origin", result.stderr)
        self.assertNotIn("Task ready", result.stderr)
        self.assertFalse((project / "tasks/fresh-task/repo").exists())
        self.assertNotEqual(self.run_command("git", "-C", clone, "show-ref", "--verify", "refs/heads/feature/fresh-task", check=False).returncode, 0)

    def test_existing_task_and_branch_can_be_reopened_offline(self):
        project = self.project()
        task = self.task(project)
        clone = project / "repo/main"
        head = self.run_command("git", "-C", task / "repo", "rev-parse", "HEAD").stdout
        (task / "repo/source.txt").write_text("Preserved local work\n")
        self.run_command("git", "-C", clone, "remote", "set-url", "origin", self.root / "missing-remote")
        self.fx("task", "fix-login", "--base", "main", "--no-attach", cwd=project)
        self.assertEqual((task / "repo/source.txt").read_text(), "Preserved local work\n")
        self.assertEqual(self.run_command("git", "-C", task / "repo", "rev-parse", "HEAD").stdout, head)
        self.run_command("git", "-C", clone, "branch", "feature/reattach", "main")
        self.assertTrue((self.task(project, "reattach") / "repo/.git").exists())

    def test_deleted_remote_base_does_not_fall_back_to_local_copy(self):
        self.run_command("git", "-C", self.origin, "branch", "develop")
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "branch", "--no-track", "develop", "origin/develop")
        self.run_command("git", "-C", self.origin, "branch", "-D", "develop")
        result = self.fx("task", "new-task", "--base", "develop", "--no-attach", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("upstream is unavailable", result.stderr)
        self.assertFalse((project / "tasks/new-task/repo").exists())

    def test_new_task_can_start_from_a_local_only_base(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "branch", "--no-track", "local-only")
        result = self.fx("task", "local-work", "--base", "local-only", "--no-attach", cwd=project)
        self.assertIn("no remote upstream", result.stderr)
        upstream = self.run_command("git", "-C", Path(result.stdout.strip()) / "repo", "rev-parse", "--symbolic-full-name", "@{upstream}")
        self.assertEqual(upstream.stdout.strip(), "refs/heads/local-only")

    def test_new_task_fetches_updates_from_the_bases_configured_remote(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "remote", "add", "upstream", self.origin)
        self.run_command("git", "-C", clone, "fetch", "upstream")
        self.run_command("git", "-C", clone, "branch", "--track", "local-base", "upstream/main")
        (self.origin / "source.txt").write_text("Upstream update\n")
        self.run_command("git", "-C", self.origin, "commit", "-am", "Update upstream")
        self.run_command("git", "-C", clone, "remote", "set-url", "origin", self.root / "missing-remote")
        result = self.fx("task", "upstream-work", "--base", "local-base", "--no-attach", cwd=project)
        task = Path(result.stdout.strip())
        self.assertEqual((task / "repo/source.txt").read_text(), "Upstream update\n")
        self.assertIn("Fetching base updates from upstream", result.stderr)

    def test_explicit_remote_base_supports_remote_names_with_slashes(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "remote", "set-url", "origin", self.root / "missing-remote")
        self.run_command("git", "-C", clone, "remote", "add", "team/upstream", self.origin)
        (self.origin / "source.txt").write_text("Selected remote update\n")
        self.run_command("git", "-C", self.origin, "commit", "-am", "Update selected remote")
        result = self.fx("task", "remote-work", "--base", "team/upstream/main", "--no-attach", cwd=project)
        task = Path(result.stdout.strip())
        self.assertEqual((task / "repo/source.txt").read_text(), "Selected remote update\n")
        self.assertEqual(self.run_command("git", "-C", task / "repo", "rev-parse", "--abbrev-ref", "@{upstream}").stdout.strip(), "team/upstream/main")

    def test_reopening_task_with_base_preserves_existing_changes(self):
        project = self.project()
        task = self.task(project)
        (task / "repo/source.txt").write_text("Preserved changes\n")
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "branch", "different-branch")
        original_head = self.run_command("git", "-C", task / "repo", "rev-parse", "HEAD").stdout
        self.fx("task", "fix-login", "--base", "different-branch", "--no-attach", cwd=project)
        self.assertEqual(self.run_command("git", "-C", task / "repo", "rev-parse", "HEAD").stdout, original_head)
        upstream = self.run_command("git", "-C", task / "repo", "rev-parse", "--symbolic-full-name", "@{upstream}")
        self.assertEqual(upstream.stdout.strip(), "refs/heads/different-branch")
        self.assertEqual((task / "repo/source.txt").read_text(), "Preserved changes\n")

    def test_invalid_base_does_not_create_a_task_branch(self):
        project = self.project()
        clone = project / "repo/main"
        self.run_command("git", "-C", clone, "tag", "release-tag")
        commit = self.run_command("git", "-C", clone, "rev-parse", "HEAD").stdout.strip()
        for base in ("missing", "bad..name", "release-tag", commit):
            with self.subTest(base=base):
                result = self.fx("task", "invalid-base", "--base", base, "--no-attach", cwd=project, check=False)
                self.assertNotEqual(result.returncode, 0)
                branch = self.run_command("git", "-C", clone, "show-ref", "--verify", "refs/heads/feature/invalid-base", check=False)
                self.assertNotEqual(branch.returncode, 0)

    def test_base_option_requires_one_value(self):
        project = self.project()
        for options in (("--base",), ("--base", ""), ("--base", "--no-attach"), ("--base", "main", "--base", "main")):
            with self.subTest(options=options):
                result = self.fx("task", "invalid-base", *options, cwd=project, check=False)
                self.assertNotEqual(result.returncode, 0)
        self.assertFalse((project / "tasks/invalid-base").exists())

    def test_shell_integration_supports_base_and_no_attach_in_either_order(self):
        for options in ("--base main --no-attach", "--no-attach --base main"):
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
        result = self.fx("task", "fix-login", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected branch", result.stderr)
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
                    result = self.fx("agent", agent, *extra, cwd=task / "repo")
                    captured = json.loads(result.stdout)
                    created = set((task / "context").iterdir()) - before
                    self.assertEqual(len(created), 1)
                    session = created.pop()
                    instructions = (session / "instructions.md").read_text()
                    self.assertFalse((session / "initial_prompt.md").exists())
                    self.assertIn(str(session / "findings.md"), instructions)
                    self.assertIn(str(project / "project_memory.md"), instructions)
                    self.assertIn("Wait for my interactive assignment", instructions)
                    self.assertEqual(captured["cwd"], str(task))
                    if agent == "claude":
                        self.assertEqual(captured["arguments"], [
                            "--model", "claude-opus-5-5", "--effort", level,
                            "--append-system-prompt-file", str(session / "instructions.md"),
                            "--add-dir", str(project / "project_context"),
                            "--settings", str(session / "claude-settings.json"),
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
                    captured = json.loads(self.fx("agent", agent, "--prompt", prompt, cwd=task).stdout)
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
                    captured = json.loads(self.fx("agent", agent, *options, cwd=task).stdout)
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
                result = self.fx("agent", agent, "--new-tab", "--prompt", prompt, "-r", "h", cwd=task / "repo")
                captured = json.loads(result.stdout)
                arguments = captured["arguments"]
                self.assertEqual(arguments[:9], [
                    "--session", "example-fix-login", "action", "new-tab",
                    "--name", agent, "--cwd", str(task), "--",
                ])
                self.assertEqual(captured["cwd"], str(task))
                self.assertEqual(arguments[9], str(TOOL.parent / "agents" / agent))
                session, = set((task / "context").iterdir()) - before
                self.assertEqual(arguments[10:], ["launch", str(task.parent.parent), str(task), str(session), "high", prompt])
                launched = json.loads(self.run_command(*arguments[9:], cwd=task).stdout)
                self.assertEqual(launched["arguments"][-2:], ["--", prompt])
                self.assertEqual(launched["cwd"], str(task))
                self.assertEqual(len(set((task / "context").iterdir()) - before), 1)
                self.assertFalse((task / "should-not-exist").exists())

    def test_new_tab_without_prompt_keeps_interactive_start(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        captured = json.loads(self.fx("agent", "codex", "-r", "l", "--new-tab", cwd=task).stdout)
        arguments = captured["arguments"]
        self.assertEqual(arguments[-1], "low")
        session, = (task / "context").iterdir()
        self.assertFalse((session / "initial_prompt.md").exists())
        launched = json.loads(self.run_command(*arguments[9:], cwd=task).stdout)
        self.assertNotIn("--", launched["arguments"])

    def test_new_tab_accepts_custom_name_in_either_flag_order(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        for agent in ("claude", "codex"):
            for options in (("--new-tab", "--name", "review"), ("--name", "Code review", "--new-tab")):
                with self.subTest(agent=agent, options=options):
                    captured = json.loads(self.fx("agent", agent, *options, "-r", "h", "--prompt", "Review changes", cwd=task).stdout)
                    arguments = captured["arguments"]
                    self.assertEqual(arguments[arguments.index("--name") + 1], options[options.index("--name") + 1])
                    self.assertEqual(arguments[-2:], ["high", "Review changes"])
                    self.assertEqual(arguments[9], str(TOOL.parent / "agents" / agent))

    def test_tab_name_requires_new_tab(self):
        task = self.task()
        result = self.fx("agent", "codex", "--name", "review", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--name requires --new-tab", result.stderr)
        self.assertEqual(list((task / "context").iterdir()), [])

    def test_invalid_tab_names_create_no_sessions(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        for options in (
            ("--name",), ("--name", ""), ("--name", "   "),
            ("--name", "review\nnext"), ("--name", "review\x1b[2J"),
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
                result = self.fx("agent", "claude", "--new-tab", cwd=task, check=False)
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
        result = self.fx("agent", "claude", "--new-tab", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Install Zellij", result.stderr)
        self.assertEqual(list((task / "context").iterdir()), [])

    def test_new_tab_failure_propagates_and_preserves_session_context(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login", FX_TEST_ZELLIJ_EXIT="23")
        result = self.fx("agent", "codex", "--new-tab", "--prompt", "Review changes", cwd=task, check=False)
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
        calls = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(calls), 2)
        group, = (task / "context/groups").iterdir()
        self.assertTrue(group.name.startswith("review-"))
        self.assertEqual((group / "initial_prompt.md").read_text(), prompt)
        self.assertEqual(list((task / "context").iterdir()), [group.parent])
        for number, (call, agent) in enumerate(zip(calls, ("claude", "codex")), 1):
            session = group / f"{number}-{agent}"
            args = call["arguments"]
            self.assertEqual(args[:9], [
                "--session", "example-fix-login", "action", "new-tab", "--name",
                f"{group.name}-{number}-{agent}", "--cwd", str(task), "--",
            ])
            self.assertEqual(args[9:], [str(TOOL.parent / "agents" / agent), "launch",
                                      str(task.parent.parent), str(task), str(session), "medium", prompt])
            self.assertEqual(call["cwd"], str(task))
            self.assertEqual((session / "initial_prompt.md").read_text(), prompt)
            self.assertEqual((session / "tab-request.txt").read_text(), "accepted\n")
            instructions = (session / "instructions.md").read_text()
            self.assertIn("This is an independent group investigation", instructions)
            self.assertIn("Do not inspect other members of this group", instructions)
            self.assertIn("Do not edit source", instructions)
            self.assertIn(str(session / "findings.md"), instructions)
            self.assertIn(session.name, (group / "group.md").read_text())
            launched = json.loads(self.run_command(*args[9:], cwd=task).stdout)
            self.assertEqual(launched["arguments"][-2:], ["--", prompt])
        self.assertFalse((task / "should-not-exist").exists())

    def test_group_custom_members_replace_defaults_and_override_reasoning(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        result = self.fx("agent", "group", "--agent", "codex:l", "--agent", "claude:h",
                         "--agent", "codex", "-r", "h", cwd=task)
        calls = [json.loads(line)["arguments"] for line in result.stdout.splitlines()]
        self.assertEqual([Path(args[9]).name for args in calls], ["codex", "claude", "codex"])
        self.assertEqual([args[-1] for args in calls], ["low", "high", "high"])
        self.assertEqual(len({args[13] for args in calls}), 3)
        for args in calls:
            session = Path(args[13])
            self.assertFalse((session / "initial_prompt.md").exists())
            self.assertIn("Wait for my interactive assignment", (session / "instructions.md").read_text())
        group, = (task / "context/groups").iterdir()
        self.assertFalse((group / "initial_prompt.md").exists())

    def test_group_default_reasoning_and_single_member(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        for options, count, reasoning in ((["-r", "l"], 2, "low"), (["--agent", "codex"], 1, "medium")):
            result = self.fx("agent", "group", *options, "--prompt", "--help", cwd=task)
            calls = [json.loads(line)["arguments"] for line in result.stdout.splitlines()]
            self.assertEqual(len(calls), count)
            self.assertTrue(all(args[-2:] == [reasoning, "--help"] for args in calls))

    def test_repeated_concurrent_groups_get_unique_directories_and_tabs(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.fx("agent", "group", "--name", "review", cwd=task), range(2)))
        groups = list((task / "context/groups").iterdir())
        self.assertEqual(len(groups), 2)
        tabs = [json.loads(line)["arguments"][5] for result in results for line in result.stdout.splitlines()]
        self.assertEqual(len(set(tabs)), 4)

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
        result = self.fx("agent", "group", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("codex CLI is not available", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(list((task / "context").iterdir()), [])

    def test_group_requires_zellij_and_a_task(self):
        task = self.task()
        result = self.fx("agent", "group", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inside a Zellij session", result.stderr)
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        result = self.fx("agent", "group", cwd=task.parent.parent, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inside a task", result.stderr)
        self.assertEqual(list((task / "context").iterdir()), [])

    def test_group_partial_tab_failure_preserves_all_context_and_stops(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        (self.bin / "zellij").write_text(
            f"#!{sys.executable}\n"
            "import json, sys\n"
            "from pathlib import Path\n"
            "args = sys.argv[1:]\n"
            "session = Path(args[13])\n"
            "assert len(list(session.parent.glob('*/instructions.md'))) == 3\n"
            "print(json.dumps({'arguments': args}))\n"
            "sys.exit(23 if session.name.startswith('2-') else 0)\n"
        )
        result = self.fx("agent", "group", "--agent", "claude", "--agent", "codex",
                         "--agent", "claude", "--prompt", "Review", cwd=task, check=False)
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 2)
        group, = (task / "context/groups").iterdir()
        for member, state in (("1-claude", "accepted"), ("2-codex", "failed: 23"), ("3-claude", "pending")):
            self.assertEqual((group / member / "tab-request.txt").read_text().strip(), state)
            self.assertEqual((group / member / "initial_prompt.md").read_text(), "Review")
        self.assertIn("Earlier tabs may still be running", result.stderr)

    def test_group_rejects_symlink_context_parent(self):
        task = self.task()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        outside = self.root / "outside"
        outside.mkdir()
        (task / "context/groups").symlink_to(outside)
        result = self.fx("agent", "group", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_parallel_launches_keep_separate_context(self):
        task = self.task()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.fx("agent", "claude", cwd=task), range(4)))
        files = [json.loads(result.stdout)["arguments"][5] for result in results]
        self.assertEqual(len(set(files)), 4)
        self.assertEqual(len(list((task / "context").iterdir())), 4)

    def test_agent_failure_preserves_context_and_exit_status(self):
        task = self.task()
        self.env["FX_TEST_AGENT_EXIT"] = "23"
        result = self.fx("agent", "codex", cwd=task, check=False)
        self.assertEqual(result.returncode, 23)
        session, = (task / "context").iterdir()
        self.assertTrue((session / "instructions.md").exists())

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
        self.fx("agent", "claude", cwd=task)
        session, = (task / "context").iterdir()
        responses = sorted((session / "results").glob("turn-*/response.md"))
        self.assertEqual([p.read_text() for p in responses], [
            "Review: missing input validation.\n", "Plan: validate before saving.\n",
        ])
        self.assertEqual((session / "findings.md").read_text(), "# Findings\n\nNo findings recorded.\n")

    def test_codex_final_response_is_captured_by_notification(self):
        task = self.task()
        executable = self.bin / "codex"
        executable.write_text(
            f"#!{sys.executable}\n"
            "import json, subprocess, sys\n"
            "for argument in sys.argv[1:]:\n"
            " if argument.startswith('notify='):\n"
            "  command = json.loads(argument.split('=', 1)[1])\n"
            "  event = {'type': 'agent-turn-complete', 'thread-id': 'codex-session', 'turn-id': 'one', 'last-assistant-message': 'Implement the reviewed plan.\\n'}\n"
            "  subprocess.run(command + [json.dumps(event)], check=True)\n"
        )
        self.fx("agent", "codex", cwd=task)
        session, = (task / "context").iterdir()
        responses = list((session / "results").glob("turn-*/response.md"))
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0].read_text(), "Implement the reviewed plan.\n")

    def test_saved_response_is_supplied_to_new_agent_and_default_index(self):
        task = self.task()
        self.fx("agent", "claude", cwd=task)
        source, = (task / "context").iterdir()
        event = json.dumps({"type": "agent-turn-complete", "thread-id": "thread", "turn-id": "turn",
                            "last-assistant-message": "The repair plan: validate the input before saving.\n"})
        self.run_command(sys.executable, TOOL.parent / "agents/codex_capture.py", "capture", source, event)
        for agent in ("codex", "claude"):
            before = set((task / "context").iterdir())
            result = self.fx("agent", agent, "--from", source, "--prompt", "Implement the saved plan", cwd=task)
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
        self.fx("agent", "codex", cwd=task)
        session, = set((task / "context").iterdir()) - before
        snapshot = (session / "input-context.md").read_text()
        self.assertIn(str(source.relative_to(task)), snapshot)
        self.assertNotIn("The repair plan", snapshot)

    def test_handoff_requires_results_in_the_current_task(self):
        project = self.project()
        task = self.task(project)
        other = self.task(project, "other")
        self.fx("agent", "claude", cwd=task)
        empty, = (task / "context").iterdir()
        for source in (empty, other / "context", task / "context/missing"):
            with self.subTest(source=source):
                before = set((task / "context").iterdir())
                result = self.fx("agent", "codex", "--from", source, cwd=task, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(set((task / "context").iterdir()), before)

    def test_groups_share_prior_result_index_by_default_and_explicit_handoff_text(self):
        task = self.task()
        self.fx("agent", "claude", cwd=task)
        source, = (task / "context").iterdir()
        event = json.dumps({"type": "agent-turn-complete", "thread-id": "thread", "turn-id": "turn",
                            "last-assistant-message": "Shared starting plan"})
        self.run_command(sys.executable, TOOL.parent / "agents/codex_capture.py", "capture", source, event)
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        for options in ([], ["--from", source]):
            result = self.fx("agent", "group", *options, cwd=task)
            sessions = [Path(json.loads(line)["arguments"][13]) for line in result.stdout.splitlines()]
            snapshots = [(session / "input-context.md").read_text() for session in sessions]
            self.assertEqual(snapshots[0], snapshots[1])
            self.assertIn(str(source.relative_to(task)), snapshots[0])
            if options:
                self.assertIn("Shared starting plan", snapshots[0])
            else:
                self.assertNotIn("Shared starting plan", snapshots[0])

    def test_group_snapshot_excludes_peer_and_later_results(self):
        task = self.task()
        self.fx("agent", "claude", cwd=task)
        source, = (task / "context").iterdir()
        capture_script = TOOL.parent / "agents/codex_capture.py"
        event = {"type": "agent-turn-complete", "thread-id": "thread", "turn-id": "before",
                 "last-assistant-message": "Earlier plan"}
        self.run_command(sys.executable, capture_script, "capture", source, json.dumps(event))
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="example-fix-login")
        previous = self.fx("agent", "group", cwd=task)
        for line in previous.stdout.splitlines():
            member = Path(json.loads(line)["arguments"][13])
            self.run_command(sys.executable, capture_script, "capture", member, json.dumps(event))
        previous_group = member.parent
        (self.bin / "zellij").write_text(
            f"#!{sys.executable}\n"
            "import json, subprocess, sys\n"
            "from pathlib import Path\n"
            "args = sys.argv[1:]\n"
            "member = Path(args[13])\n"
            "if member.name.startswith('1-'):\n"
            f" event = {event!r}\n"
            " event['turn-id'] = 'after'\n"
            " event['last-assistant-message'] = 'Late result'\n"
            f" for target in (member, Path({str(source)!r})):\n"
            f"  subprocess.run([sys.executable, {str(capture_script)!r}, 'capture', str(target), json.dumps(event)], check=True)\n"
            "print(json.dumps({'arguments': args}))\n"
        )
        result = self.fx("agent", "group", cwd=task)
        members = [Path(json.loads(line)["arguments"][13]) for line in result.stdout.splitlines()]
        snapshots = [(member / "input-context.md").read_text() for member in members]
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertIn(str(source.relative_to(task) / "results/turn-000001/response.md"), snapshots[0])
        self.assertIn(str(previous_group.relative_to(task)), snapshots[0])
        self.assertNotIn("turn-000002", snapshots[0])
        self.assertNotIn(str(members[0].relative_to(task)), snapshots[0])
        self.assertTrue((source / "results/turn-000002/response.md").exists())
        self.assertTrue((members[0] / "results/turn-000001/response.md").exists())
        for member in members:
            instructions = (member / "instructions.md").read_text()
            self.assertIn("Read earlier captured responses listed in your starting context snapshot", instructions)
            self.assertIn("Do not inspect other members of this group", instructions)

    def test_commands_require_the_correct_working_directory(self):
        project = self.project()
        self.assertNotEqual(self.fx("task", "fix", check=False).returncode, 0)
        self.assertNotEqual(self.fx("agent", "claude", cwd=project, check=False).returncode, 0)

    def test_compare_group_uses_default_agent_and_captured_member_results(self):
        task = self.task()
        group = self.completed_group(task)
        result = self.fx("agent", "group", "compare", "review", cwd=task / "repo")
        args = json.loads(result.stdout)["arguments"]
        self.assertIn('model_reasoning_effort="medium"', args)
        self.assertIn("gpt-6.1-sol", args)
        comparison, = (group / "comparisons").iterdir()
        self.assertEqual((comparison / "source-group.txt").read_text().strip(), str(group))
        instructions = (comparison / "instructions.md").read_text()
        self.assertIn("Review from 1-claude", instructions)
        self.assertIn("Review from 2-codex", instructions)
        self.assertIn("Review the login changes.", instructions)
        self.assertNotIn("This is an independent group investigation", instructions)
        self.assertEqual(json.loads(args[7].split("=", 1)[1]), instructions.rstrip("\n"))
        self.assertEqual((comparison / "initial_prompt.md").read_text(), args[-1])
        self.assertIn("Compare and merge", args[-1])
        self.assertIn("Do not edit repository files", args[-1])
        self.assertEqual(list((task / "context").iterdir()), [group.parent])

    def test_compare_can_use_claude_high_reasoning_in_new_tab(self):
        task = self.task()
        group = self.completed_group(task)
        result = self.fx("agent", "group", "compare", group.name, "--agent", "claude", "-r", "h", "--new-tab", cwd=task)
        args = json.loads(result.stdout)["arguments"]
        self.assertEqual(args[5], f"{group.name}-compare")
        self.assertEqual(args[9], str(TOOL.parent / "agents/claude"))
        self.assertEqual(args[-2], "high")
        comparison, = (group / "comparisons").iterdir()
        self.assertEqual(args[13], str(comparison))
        launched = json.loads(self.run_command(*args[9:], cwd=task).stdout)["arguments"]
        self.assertEqual(launched[3], "high")
        self.assertEqual(launched[-1], (comparison / "initial_prompt.md").read_text())

    def test_compare_rejects_missing_member_results_without_creating_session(self):
        task = self.task()
        group = self.completed_group(task)
        shutil.rmtree(group / "2-codex/results")
        result = self.fx("agent", "group", "compare", "review", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("2-codex", result.stderr)
        self.assertFalse((group / "comparisons").exists())
        self.assertEqual(result.stdout, "")

    def test_compare_rejects_ambiguous_name_but_accepts_full_name(self):
        task = self.task()
        first = self.completed_group(task)
        second = self.completed_group(task)
        result = self.fx("agent", "group", "compare", "review", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(first.name, result.stderr)
        self.assertIn(second.name, result.stderr)
        self.assertFalse((first / "comparisons").exists())
        self.assertFalse((second / "comparisons").exists())
        self.fx("agent", "group", "compare", first.name, cwd=task)
        self.assertTrue((first / "comparisons").is_dir())

    def test_repeated_comparisons_capture_results_and_do_not_feed_previous_merges_back(self):
        task = self.task()
        group = self.completed_group(task)
        self.fx("agent", "group", "compare", "review", cwd=task)
        first, = (group / "comparisons").iterdir()
        event = {"type": "agent-turn-complete", "thread-id": "comparison", "turn-id": "one",
                 "last-assistant-message": "Merged report: add validation and tests."}
        self.run_command(sys.executable, TOOL.parent / "agents/codex_capture.py", "capture", first, json.dumps(event))
        self.fx("agent", "group", "compare", "review", cwd=task)
        second, = set((group / "comparisons").iterdir()) - {first}
        self.assertNotIn("Merged report", (second / "input-context.md").read_text())
        result = self.fx("agent", "claude", "--from", first, cwd=task)
        instructions = Path(json.loads(result.stdout)["arguments"][5]).read_text()
        self.assertIn("Merged report: add validation and tests.", instructions)
        result = self.fx("agent", "claude", cwd=task)
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
        request = group / "1-claude/tab-request.txt"
        request.write_text("failed: 23\n")
        result = self.fx("agent", "group", "compare", "review", cwd=task, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not accepted", result.stderr)
        request.write_text("accepted\n")
        (group / "2-codex/capture-error.txt").write_text("Capture failed")
        result = self.fx("agent", "group", "compare", "review", cwd=task, check=False)
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
                "arguments": ["attach", "--create", "example-fix-login", "options", "--default-cwd", str(task)],
                "cwd": str(task),
            })
            self.assertTrue((task / "repo/.git").is_file())

    def test_task_switches_sessions_when_inside_zellij(self):
        project = self.project()
        self.env.update(ZELLIJ="0", ZELLIJ_SESSION_NAME="previous-task")
        task = project / "tasks/next-task"
        captured = json.loads(self.fx("task", "next-task", cwd=project).stdout)
        self.assertEqual(captured, {
            "arguments": ["action", "switch-session", "example-next-task", "--cwd", str(task)],
            "cwd": str(task),
        })

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
        self.assertEqual(captured["arguments"][:3], ["attach", "--create", "example-fix-login"])

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
        self.assertEqual(captured["arguments"][:3], ["attach", "--create", "example-fix-login"])

    def test_same_task_name_in_different_projects_uses_distinct_sessions(self):
        first_project = self.project()
        second_project = Path(self.fx("setup", "another-project", self.origin).stdout.strip())
        first = json.loads(self.fx("task", "fix-login", cwd=first_project).stdout)
        second = json.loads(self.fx("task", "fix-login", cwd=second_project).stdout)
        self.assertEqual(first["arguments"][2], "example-fix-login")
        self.assertEqual(second["arguments"][2], "another-project-fix-login")

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
