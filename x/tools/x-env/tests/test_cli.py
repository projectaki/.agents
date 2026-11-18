"""Integration tests, ported from fx tests/test_fx.py (setup, task, onto, base,
local-file copying, delete). They drive the `x-env` CLI against real
temporary git repositories in a temporary X_ENV_ROOT."""

import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "x-env"


class CliTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="x-env test ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.env = {
            k: v for k, v in os.environ.items()
            if not k.startswith(("GIT_", "X_ENV_")) and k not in ("BASH_ENV", "ENV", "CDPATH")
        }
        self.env.update(
            HOME=str(self.home),
            X_ENV_ROOT=str(self.root / 'work with "quotes" and $dollars'),
            PATH=f"{self.bin}:{os.environ['PATH']}",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="Test",
            GIT_AUTHOR_EMAIL="test@example.invalid",
            GIT_COMMITTER_NAME="Test",
            GIT_COMMITTER_EMAIL="test@example.invalid",
        )
        self.origin = self.root / "origin"
        self.git("init", "-b", "main", self.origin)
        (self.origin / "source.txt").write_text("original\n")
        self.git("-C", self.origin, "add", ".")
        self.git("-C", self.origin, "commit", "-m", "Initial source")

    # --- helpers --------------------------------------------------------------

    def run_command(self, *arguments, cwd=None, check=True, **options):
        return subprocess.run(
            [str(a) for a in arguments], cwd=cwd or self.root, env=self.env,
            text=True, capture_output=True, check=check, **options,
        )

    def git(self, *arguments, cwd=None, check=True):
        return self.run_command("git", *arguments, cwd=cwd, check=check)

    def out(self, *arguments, cwd=None):
        return self.git(*arguments, cwd=cwd).stdout.strip()

    def has_ref(self, repository, ref):
        return self.git("-C", repository, "show-ref", "--verify", "--quiet", ref, check=False).returncode == 0

    def branch(self, worktree):
        return self.out("-C", worktree, "branch", "--show-current")

    def upstream(self, worktree, branch="HEAD"):
        result = self.git("-C", worktree, "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}", check=False)
        return result.stdout.strip() if result.returncode == 0 else None

    def x_env(self, *arguments, cwd=None, check=True, **options):
        return self.run_command(TOOL, *arguments, cwd=cwd, check=check, **options)

    def project(self):
        return Path(self.x_env("setup", "example", self.origin).stdout.strip())

    def task(self, project=None, name="fix-login", *options):
        project = project or self.project()
        return Path(self.x_env("task", name, *options, cwd=project).stdout.strip())

    def worktrees(self, project):
        return self.out("-C", project / "repo/main", "worktree", "list", "--porcelain")

    def assert_fails(self, result, message=None, code=1):
        self.assertEqual(result.returncode, code, result.stderr)
        self.assertEqual(result.stdout, "")
        if message is not None:
            self.assertIn(message, result.stderr)


class SetupTest(CliTest):
    def test_setup_reuses_clone_and_preserves_dirty_files(self):
        project = self.project()
        self.assertEqual(project, Path(self.env["X_ENV_ROOT"]) / "example")
        source = project / "repo/main/source.txt"
        source.write_text("Uncommitted edit\n")
        self.assertEqual(self.x_env("setup", "example", self.origin).stdout.strip(), str(project))
        self.assertEqual(source.read_text(), "Uncommitted edit\n")
        self.assertEqual(self.x_env("setup", "example").stdout.strip(), str(project))
        self.assertTrue((project / "tasks").is_dir())
        self.assertTrue((project / "sessions").is_dir())

    def test_setup_warns_until_claude_trusts_the_root(self):
        warning = "Claude Code does not trust"
        self.assertIn(warning, self.x_env("setup", "example").stderr)  # no ~/.claude.json
        (self.home / ".claude.json").write_text("not json")
        self.assertIn(warning, self.x_env("setup", "example").stderr)
        trusted = {"projects": {str(self.root): {"hasTrustDialogAccepted": True}}}
        (self.home / ".claude.json").write_text(json.dumps(trusted))
        self.assertNotIn(warning, self.x_env("setup", "example").stderr)

    def test_setup_without_repository_can_add_repository_later(self):
        project = Path(self.x_env("setup", "example").stdout.strip())
        self.assertFalse((project / "repo/main").exists())
        self.assert_fails(self.x_env("task", "fix", cwd=project, check=False), "x-env setup example")
        self.assertFalse((project / "tasks/fix").exists())
        self.assertTrue((self.project() / "repo/main/.git").is_dir())

    def test_setup_rejects_different_origin(self):
        project = self.project()
        result = self.x_env("setup", "example", "someone/another-repository", check=False)
        self.assert_fails(result, "differs")
        self.assertEqual(self.out("-C", project / "repo/main", "remote", "get-url", "origin"), str(self.origin))

    def test_setup_accepts_the_same_github_repository_in_another_form(self):
        project = self.project()
        self.git("-C", project / "repo/main", "remote", "set-url", "origin", "git@github.com:owner/repo.git")
        for repository in ("owner/repo", "https://github.com/owner/repo.git", "ssh://git@github.com/owner/repo"):
            with self.subTest(repository=repository):
                self.assertEqual(self.x_env("setup", "example", repository).stdout.strip(), str(project))

    def test_failed_clone_does_not_report_success_and_can_retry(self):
        self.assert_fails(self.x_env("setup", "example", self.root / "missing", check=False))
        self.assertTrue((self.project() / "repo/main/.git").is_dir())

    def test_partial_clone_left_by_a_killed_setup_is_removed(self):
        project = Path(self.x_env("setup", "example").stdout.strip())
        partial = project / "repo/.main-partial-dead"
        partial.mkdir()
        (partial / "half-written").write_text("partial\n")
        self.project()
        self.assertFalse(partial.exists())
        self.assertEqual(sorted(p.name for p in (project / "repo").iterdir()), ["main"])

    def test_names_cannot_escape_the_project(self):
        for name in ("../escape", "a/b", "-option", "", "with spaces", "a;echo", "a\nline"):
            with self.subTest(name=name):
                result = self.x_env("setup", "--", name, check=False)
                self.assert_fails(result, "Names must", code=2)
        self.assertFalse(Path(self.env["X_ENV_ROOT"]).exists())

    def test_commands_require_a_project(self):
        for command in (("task", "fix"), ("delete", "fix")):
            with self.subTest(command=command):
                self.assert_fails(self.x_env(*command, cwd=self.root, check=False), "inside a project")

    def test_project_option_selects_the_project_from_anywhere(self):
        project = self.project()
        result = self.x_env("--project", "example", "task", "fix-login", cwd=self.root)
        self.assertEqual(result.stdout.strip(), str(project / "tasks/fix-login"))
        self.x_env("--project", "example", "delete", "fix-login", cwd=self.root)
        self.assertFalse((project / "tasks/fix-login").exists())


class TaskTest(CliTest):
    def test_task_reuses_worktree_and_preserves_dirty_source_and_instructions(self):
        project = self.project()
        task = self.task(project)
        self.assertEqual(task, project / "tasks/fix-login")
        (task / "repo/source.txt").write_text("Task changes\n")
        (task / "AGENTS.md").write_text("Custom instructions\n")
        result = self.x_env("task", "fix-login", cwd=task / "repo")
        self.assertEqual(result.stdout.strip(), str(task))
        self.assertEqual((task / "repo/source.txt").read_text(), "Task changes\n")
        self.assertEqual((task / "AGENTS.md").read_text(), "Custom instructions\n")
        self.assertEqual((project / "repo/main/source.txt").read_text(), "original\n")

    def test_task_instructions_name_the_source_and_records(self):
        project = self.project()
        instructions = (self.task(project) / "AGENTS.md").read_text()
        self.assertIn(str(project / "tasks/fix-login/repo"), instructions)
        self.assertIn(str(project / "sessions/fix-login"), instructions)
        self.assertIn("Only one session edits the source worktree at a time.", instructions)

    def test_tasks_have_separate_worktrees(self):
        project = self.project()
        first = self.task(project, "first")
        second = self.task(project, "second")
        (first / "repo/source.txt").write_text("First task changes\n")
        self.assertEqual((second / "repo/source.txt").read_text(), "original\n")
        self.assertEqual(self.branch(second / "repo"), "feature/second")

    def test_new_task_uses_fetched_default_instead_of_current_checkout(self):
        project = self.project()
        clone = project / "repo/main"
        self.git("-C", clone, "switch", "-c", "unrelated")
        (clone / "source.txt").write_text("Unrelated branch change\n")
        self.git("-C", clone, "commit", "-am", "Unrelated change")
        (self.origin / "source.txt").write_text("Latest default\n")
        self.git("-C", self.origin, "commit", "-am", "Default change")
        task = self.task(project)
        self.assertEqual((task / "repo/source.txt").read_text(), "Latest default\n")
        self.assertEqual((clone / "source.txt").read_text(), "Unrelated branch change\n")
        self.assertEqual(self.branch(task / "repo"), "feature/fix-login")
        self.assertEqual(self.upstream(task / "repo"), "origin/main")

    def test_default_branch_discovery_supports_non_main_names(self):
        self.git("-C", self.origin, "branch", "-m", "trunk")
        project = self.project()
        self.git("-C", project / "repo/main", "remote", "set-head", "origin", "--delete")
        task = self.task(project)
        self.assertEqual(self.upstream(task / "repo"), "origin/trunk")

    def test_reopening_the_same_branch_preserves_dirty_files_and_works_offline(self):
        project = self.project()
        task = self.task(project)
        (task / "repo/source.txt").write_text("Preserved local work\n")
        self.git("-C", project / "repo/main", "remote", "set-url", "origin", self.root / "missing-remote")
        for options in ((), ("--base", "feature/fix-login")):
            with self.subTest(options=options):
                self.x_env("task", "fix-login", *options, cwd=project)
                self.assertEqual((task / "repo/source.txt").read_text(), "Preserved local work\n")

    def test_task_does_not_reset_a_switched_branch(self):
        task = self.task()
        self.git("-C", task / "repo", "switch", "-c", "manual-branch")
        self.x_env("task", "fix-login", cwd=task)
        self.assertEqual(self.branch(task / "repo"), "manual-branch")

    def test_task_reattaches_existing_branch(self):
        project = self.project()
        self.git("-C", project / "repo/main", "branch", "fix-login")
        task = self.task(project)
        self.assertEqual(self.branch(task / "repo"), "fix-login")

    def test_task_reattaches_legacy_branch_and_keeps_its_upstream(self):
        project = self.project()
        self.git("-C", project / "repo/main", "branch", "--track", "codex/fix-login", "origin/main")
        task = self.task(project)
        self.assertEqual(self.branch(task / "repo"), "codex/fix-login")
        self.assertEqual(self.upstream(task / "repo"), "origin/main")

    def test_default_fetch_failure_creates_no_branch_or_worktree(self):
        project = self.project()
        clone = project / "repo/main"
        self.git("-C", clone, "remote", "set-url", "origin", self.root / "missing-remote")
        self.assert_fails(self.x_env("task", "review", cwd=project, check=False), "Could not fetch origin")
        self.assertFalse((project / "tasks/review").exists())
        self.assertFalse(self.has_ref(clone, "refs/heads/feature/review"))

    def test_task_rejects_foreign_worktree(self):
        project = self.project()
        task = project / "tasks/fix-login"
        task.mkdir()
        self.git("-C", self.origin, "worktree", "add", "-b", "foreign", task / "repo")
        self.assert_fails(self.x_env("task", "fix-login", cwd=project, check=False), "another repository")

    def test_task_rejects_detached_worktree(self):
        task = self.task()
        self.git("-C", task / "repo", "switch", "--detach")
        self.assert_fails(self.x_env("task", "fix-login", cwd=task, check=False), "no checked-out branch")

    def test_managed_directories_cannot_be_symlinks(self):
        project = self.project()
        outside = self.root / "outside"
        outside.mkdir()
        (project / "tasks/redirect").symlink_to(outside, target_is_directory=True)
        self.assert_fails(self.x_env("task", "redirect", cwd=project, check=False), "symbolic link")
        self.assertEqual(list(outside.iterdir()), [])

    def test_shell_integration_changes_directory_only_after_success(self):
        shells = ["bash"] + (["zsh"] if shutil.which("zsh") else [])
        for shell in shells:
            with self.subTest(shell=shell):
                result = self.run_command(shell, "-c", '''
eval "$("$1" shell-init)"
x-env setup example "$2" || exit
pwd -P
x-env task fix-login --base export || exit
pwd -P
x-env task ../invalid >/dev/null 2>&1 && exit 1
pwd -P
''', "test", TOOL, self.origin)
                project = Path(self.env["X_ENV_ROOT"]) / "example"
                task = project / "tasks/fix-login"
                self.assertEqual(result.stdout.splitlines(), [str(project), str(task), str(task)])
                self.x_env("delete", "fix-login", cwd=project)


class BaseTest(CliTest):
    def test_explicit_base_checks_out_existing_local_branch_with_its_own_commits(self):
        project = self.project()
        clone = project / "repo/main"
        self.git("-C", clone, "switch", "-c", "feature/export")
        (clone / "source.txt").write_text("Local export changes\n")
        self.git("-C", clone, "commit", "-am", "Export changes")
        self.git("-C", clone, "branch", "--set-upstream-to=origin/main")
        expected = self.out("-C", clone, "rev-parse", "HEAD")
        self.git("-C", clone, "switch", "main")
        task = self.task(project, "review", "--base", "feature/export")
        self.assertEqual(self.branch(task / "repo"), "feature/export")
        self.assertEqual(self.out("-C", task / "repo", "rev-parse", "HEAD"), expected)
        self.assertEqual(self.upstream(task / "repo"), "origin/main")
        self.assertFalse(self.has_ref(clone, "refs/heads/feature/review"))
        self.x_env("task", "review", cwd=task)
        self.assertEqual(self.branch(task / "repo"), "feature/export")

    def test_explicit_base_overrides_an_old_task_branch_without_resetting_it(self):
        project = self.project()
        worktree = self.task(project, "review") / "repo"
        (worktree / "source.txt").write_text("Unrelated work\n")
        self.git("-C", worktree, "commit", "-am", "Unrelated work")
        old_head = self.out("-C", worktree, "rev-parse", "HEAD")
        self.git("-C", self.origin, "switch", "-c", "feature/export")
        (self.origin / "source.txt").write_text("Export changes\n")
        self.git("-C", self.origin, "commit", "-am", "Export changes")
        expected = self.out("-C", self.origin, "rev-parse", "HEAD")
        self.x_env("task", "review", "--base", "origin/feature/export", cwd=project)
        self.assertEqual(self.branch(worktree), "feature/export")
        self.assertEqual(self.out("-C", worktree, "rev-parse", "HEAD"), expected)
        self.assertEqual(self.out("-C", worktree, "rev-parse", "feature/review"), old_head)
        self.assertEqual(self.upstream(worktree, "feature/review"), "origin/main")
        self.assertEqual(self.upstream(worktree), "origin/feature/export")

    def test_explicit_base_ignores_an_existing_task_branch_without_a_worktree(self):
        project = self.project()
        clone = project / "repo/main"
        self.git("-C", clone, "branch", "feature/review")
        self.git("-C", clone, "branch", "export")
        task = self.task(project, "review", "--base", "export")
        self.assertEqual(self.branch(task / "repo"), "export")

    def test_remote_base_creates_a_local_tracking_branch_at_the_fetched_commit(self):
        project = self.project()
        for name, prefix in (("local", ""), ("remote", "origin/")):
            with self.subTest(prefix=prefix):
                branch = f"feature/export-{name}"
                self.git("-C", self.origin, "switch", "-c", branch, "main")
                (self.origin / "source.txt").write_text(branch + "\n")
                self.git("-C", self.origin, "commit", "-am", "Export changes")
                expected = self.out("-C", self.origin, "rev-parse", "HEAD")
                worktree = self.task(project, name, "--base", prefix + branch) / "repo"
                self.assertEqual(self.branch(worktree), branch)
                self.assertEqual(self.out("-C", worktree, "rev-parse", "HEAD"), expected)
                self.assertEqual(self.upstream(worktree), f"origin/{branch}")

    def test_explicit_remote_reuses_local_branch_without_resetting_commits_or_upstream(self):
        project = self.project()
        clone = project / "repo/main"
        self.git("-C", clone, "branch", "--track", "export", "origin/main")
        self.git("-C", clone, "switch", "export")
        (clone / "source.txt").write_text("Unpushed local changes\n")
        self.git("-C", clone, "commit", "-am", "Local export changes")
        expected = self.out("-C", clone, "rev-parse", "HEAD")
        self.git("-C", clone, "switch", "main")
        self.git("-C", self.origin, "branch", "export")
        worktree = self.task(project, "review", "--base", "origin/export") / "repo"
        self.assertEqual(self.branch(worktree), "export")
        self.assertEqual(self.upstream(worktree), "origin/main")
        self.assertEqual(self.out("-C", worktree, "rev-parse", "HEAD"), expected)

    def test_explicit_remote_base_supports_remote_names_with_slashes(self):
        project = self.project()
        clone = project / "repo/main"
        self.git("-C", clone, "remote", "set-url", "origin", self.root / "missing-remote")
        self.git("-C", clone, "remote", "add", "team/upstream", self.origin)
        self.git("-C", self.origin, "switch", "-c", "feature/export")
        (self.origin / "source.txt").write_text("Selected remote update\n")
        self.git("-C", self.origin, "commit", "-am", "Update selected remote")
        worktree = self.task(project, "review", "--base", "team/upstream/feature/export") / "repo"
        self.assertEqual((worktree / "source.txt").read_text(), "Selected remote update\n")
        self.assertEqual(self.branch(worktree), "feature/export")
        self.assertEqual(self.upstream(worktree), "team/upstream/feature/export")

    def test_missing_base_is_checked_out_from_latest_default_without_changing_main(self):
        project = self.project()
        clone = project / "repo/main"
        (clone / "source.txt").write_text("Local work\n")
        (self.origin / "source.txt").write_text("Latest default\n")
        self.git("-C", self.origin, "commit", "-am", "Update default")
        expected = self.out("-C", self.origin, "rev-parse", "HEAD")
        worktree = self.task(project, "review", "--base", "release/new") / "repo"
        self.assertEqual(self.branch(worktree), "release/new")
        self.assertEqual(self.out("-C", worktree, "rev-parse", "HEAD"), expected)
        self.assertIsNone(self.upstream(worktree))
        self.assertEqual((clone / "source.txt").read_text(), "Local work\n")
        self.assertEqual(self.branch(clone), "main")

    def test_existing_local_branch_works_with_a_missing_upstream(self):
        project = self.project()
        clone = project / "repo/main"
        self.git("-C", clone, "branch", "--track", "export", "origin/main")
        self.git("-C", clone, "config", "branch.export.merge", "refs/heads/missing")
        self.git("-C", clone, "remote", "set-url", "origin", self.root / "missing-remote")
        worktree = self.task(project, "review", "--base", "export") / "repo"
        self.assertEqual(self.branch(worktree), "export")
        self.assertEqual(self.out("-C", clone, "config", "branch.export.merge"), "refs/heads/missing")

    def test_branch_checked_out_elsewhere_is_rejected(self):
        project = self.project()
        result = self.x_env("task", "review", "--base", "main", cwd=project, check=False)
        self.assert_fails(result, "already checked out")
        self.assertFalse((project / "tasks/review").exists())
        self.assertEqual(self.branch(project / "repo/main"), "main")

    def test_reopening_cannot_take_a_branch_from_another_worktree(self):
        project = self.project()
        worktree = self.task(project) / "repo"
        result = self.x_env("task", "fix-login", "--base", "main", cwd=project, check=False)
        self.assert_fails(result, "already checked out")
        self.assertEqual(self.branch(worktree), "feature/fix-login")

    def test_switching_task_branch_rejects_uncommitted_and_untracked_files(self):
        project = self.project()
        worktree = self.task(project) / "repo"
        self.git("-C", worktree, "branch", "export")
        for relative in ("source.txt", "new.txt"):
            with self.subTest(relative=relative):
                source = worktree / relative
                source.write_text("Uncommitted work\n")
                result = self.x_env("task", "fix-login", "--base", "export", cwd=project, check=False)
                self.assert_fails(result, "uncommitted")
                self.assertEqual(source.read_text(), "Uncommitted work\n")
                self.assertEqual(self.branch(worktree), "feature/fix-login")
                if relative == "source.txt":
                    self.git("-C", worktree, "restore", "source.txt")
                else:
                    source.unlink()
        self.x_env("task", "fix-login", "--base", "export", cwd=project)
        self.assertEqual(self.branch(worktree), "export")

    def test_switching_preserves_ignored_files_that_the_target_branch_tracks(self):
        project = self.project()
        task = self.task(project)
        clone = project / "repo/main"
        (clone / "settings.json").write_text("Tracked target settings\n")
        self.git("-C", clone, "add", "settings.json")
        self.git("-C", clone, "commit", "-m", "Track settings")
        self.git("-C", clone, "branch", "export")
        self.git("-C", task / "repo", "config", "core.excludesFile", self.root / "ignore")
        (self.root / "ignore").write_text("settings.json\n")
        settings = task / "repo/settings.json"
        settings.write_text("Private settings\n")
        self.assert_fails(self.x_env("task", "fix-login", "--base", "export", cwd=task, check=False))
        self.assertEqual(settings.read_text(), "Private settings\n")
        self.assertEqual(self.branch(task / "repo"), "feature/fix-login")

    def test_missing_remote_base_is_not_created_as_local_branch(self):
        project = self.project()
        clone = project / "repo/main"
        self.git("-C", clone, "remote", "add", "team/upstream", self.origin)
        for base in ("origin/missing", "team/upstream/missing"):
            with self.subTest(base=base):
                result = self.x_env("task", "review", "--base", base, cwd=project, check=False)
                self.assert_fails(result, "Remote base branch not found")
                self.assertFalse(self.has_ref(clone, f"refs/heads/{base}"))
                self.assertFalse(self.has_ref(clone, "refs/heads/missing"))
        self.assertFalse((project / "tasks/review").exists())

    def test_fetch_failure_creates_no_branch_or_worktree(self):
        project = self.project()
        clone = project / "repo/main"
        self.git("-C", clone, "remote", "set-url", "origin", self.root / "missing-remote")
        for base in ("new-base", "origin/export"):
            with self.subTest(base=base):
                result = self.x_env("task", "review", "--base", base, cwd=project, check=False)
                self.assert_fails(result, "Could not fetch origin")
                self.assertFalse((project / "tasks/review").exists())
                self.assertFalse(self.has_ref(clone, "refs/heads/new-base"))

    def test_invalid_base_does_not_create_a_task_branch(self):
        project = self.project()
        clone = project / "repo/main"
        self.git("-C", clone, "tag", "release-tag")
        commit = self.out("-C", clone, "rev-parse", "HEAD")
        for base, code in (("origin/missing", 1), ("bad..name", 2), ("release-tag", 1), (commit, 1)):
            with self.subTest(base=base):
                self.assert_fails(self.x_env("task", "review", "--base", base, cwd=project, check=False), code=code)
                self.assertFalse((project / "tasks/review").exists())
        self.assertEqual(self.out("-C", clone, "for-each-ref", "--format=%(refname)", "refs/heads"), "refs/heads/main")

    def test_base_option_requires_one_value(self):
        project = self.project()
        for options in (("--base",), ("--base", ""), ("--base", "--force"), ("--base", "main", "--base", "main")):
            with self.subTest(options=options):
                self.assert_fails(self.x_env("task", "invalid-base", *options, cwd=project, check=False), code=2)
        self.assertFalse((project / "tasks/invalid-base").exists())


class OntoTest(CliTest):
    def test_onto_creates_a_named_branch_from_another_task(self):
        project = self.project()
        parent = self.task(project, "export") / "repo"
        (parent / "source.txt").write_text("Local export changes\n")
        self.git("commit", "-am", "Export changes", cwd=parent)
        parent_head = self.out("rev-parse", "HEAD", cwd=parent)
        worktree = self.task(project, "validation", "--onto", "feature/export",
                             "--branch", "feature/export-validation") / "repo"
        self.assertEqual(self.branch(worktree), "feature/export-validation")
        self.assertEqual(self.out("rev-parse", "HEAD", cwd=worktree), parent_head)
        self.assertIsNone(self.upstream(worktree))
        self.assertEqual(self.out("rev-parse", "HEAD", cwd=parent), parent_head)
        self.x_env("task", "validation", cwd=project)
        self.assertEqual(self.branch(worktree), "feature/export-validation")

    def test_onto_uses_the_fetched_remote_tip_without_creating_a_local_start_branch(self):
        project = self.project()
        clone = project / "repo/main"
        self.git("branch", "export", cwd=clone)
        self.git("switch", "-c", "export", cwd=self.origin)
        (self.origin / "source.txt").write_text("Pushed export changes\n")
        self.git("commit", "-am", "Export changes", cwd=self.origin)
        self.git("branch", "remote-only", cwd=self.origin)
        remote_head = self.out("rev-parse", "HEAD", cwd=self.origin)
        self.git("remote", "add", "feature", self.origin, cwd=clone)
        self.git("remote", "add", "team/upstream", self.origin, cwd=clone)
        for name, onto in (("explicit", "origin/export"), ("fallback", "remote-only"),
                           ("other-remote", "team/upstream/export")):
            with self.subTest(onto=onto):
                worktree = self.task(project, name, "--onto", onto) / "repo"
                self.assertEqual(self.branch(worktree), f"feature/{name}")
                self.assertEqual(self.out("rev-parse", "HEAD", cwd=worktree), remote_head)
                self.assertIsNone(self.upstream(worktree))
        self.assertFalse(self.has_ref(clone, "refs/heads/remote-only"))

    def test_onto_rejects_unavailable_branches_without_creating_a_worktree(self):
        project = self.project()
        clone = project / "repo/main"
        self.git("branch", "local-export", cwd=clone)
        self.git("branch", "remote-export", cwd=self.origin)
        self.git("tag", "export-tag", cwd=clone)
        for destination, onto, error, code in (
            ("new..export", "main", "Invalid branch for --branch", 2),
            ("new-export", "bad..branch", "Invalid branch for --onto", 2),
            ("local-export", "main", "Use a new branch name", 1),
            ("export-tag", "main", "Use a new branch name", 1),
            ("remote-export", "main", "Branch already exists on origin", 1),
            ("new-export", "missing", "Start branch for --onto not found", 1),
            ("new-export", "export-tag", "Start branch for --onto not found", 1),
        ):
            with self.subTest(destination=destination, onto=onto):
                result = self.x_env("task", "validation", "--onto", onto, "--branch", destination,
                                    cwd=project, check=False)
                self.assert_fails(result, error, code=code)
                self.assertFalse((project / "tasks/validation").exists())
        for branch in ("remote-export", "new-export"):
            self.assertFalse(self.has_ref(clone, f"refs/heads/{branch}"))

    def test_onto_rejects_an_existing_task_without_switching_branches(self):
        project = self.project()
        worktree = self.task(project) / "repo"
        (worktree / "source.txt").write_text("Uncommitted work\n")
        result = self.x_env("task", "fix-login", "--onto", "main", "--branch", "another-branch",
                            cwd=project, check=False)
        self.assert_fails(result, "Omit --onto to reopen it")
        self.assertEqual(self.branch(worktree), "feature/fix-login")
        self.assertEqual((worktree / "source.txt").read_text(), "Uncommitted work\n")
        self.assertFalse(self.has_ref(worktree, "refs/heads/another-branch"))

    def test_base_and_branch_options_are_usage_errors_next_to_and_without_onto(self):
        project = self.project()
        for options in (("--onto", "main", "--base", "feature/x"), ("--branch", "feature/x")):
            with self.subTest(options=options):
                self.assert_fails(self.x_env("task", "validation", *options, cwd=project, check=False), code=2)
        self.assertFalse((project / "tasks/validation").exists())


class LocalFilesTest(CliTest):
    def test_task_copies_ignored_files_with_paths_and_permissions(self):
        (self.origin / ".gitignore").write_text("appsettings*.json\n.env\nignored-dir/\n")
        self.git("-C", self.origin, "add", ".gitignore")
        self.git("-C", self.origin, "commit", "-m", "Ignore local settings")
        project = self.project()
        clone = project / "repo/main"
        paths = ("appsettings.json", "src/My App/appsettings.Development.json",
                 "ignored-dir/nested/appsettings.Local.json")
        for relative in paths:
            source = clone / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text('{"LocalSetting": "test-only"}\n')
            source.chmod(0o600)
        (clone / ".env").write_text("LOCAL_VALUE=1\n")
        (clone / "ignored-dir/unrelated.txt").write_text("Nested local file\n")
        worktree = self.task(project) / "repo"
        for relative in paths:
            target = worktree / relative
            self.assertEqual(target.read_bytes(), (clone / relative).read_bytes())
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual((worktree / ".env").read_text(), "LOCAL_VALUE=1\n")
        self.assertEqual((worktree / "ignored-dir/unrelated.txt").read_text(), "Nested local file\n")
        self.assertEqual(self.out("-C", worktree, "status", "--porcelain"), "")
        self.assertEqual(list(worktree.rglob(".x-env-copy-*")), [])

    def test_task_fills_missing_settings_without_overwriting_existing_settings(self):
        project = self.project()
        clone = project / "repo/main"
        (clone / ".git/info/exclude").write_text("appsettings*.json\n")
        task = self.task(project)
        (clone / "appsettings.Local.json").write_text("main local settings\n")
        self.x_env("task", "fix-login", cwd=task)
        self.assertEqual((task / "repo/appsettings.Local.json").read_text(), "main local settings\n")
        (task / "repo/appsettings.Local.json").write_text("task local settings\n")
        (clone / "appsettings.Local.json").write_text("updated main settings\n")
        (clone / "appsettings.Development.json").write_text("new development settings\n")
        self.x_env("task", "fix-login", cwd=task)
        self.assertEqual((task / "repo/appsettings.Local.json").read_text(), "task local settings\n")
        self.assertEqual((task / "repo/appsettings.Development.json").read_text(), "new development settings\n")

    def test_copy_uses_main_clone_ignore_rules_and_skips_unselected_files(self):
        project = self.project()
        clone = project / "repo/main"
        (clone / ".gitignore").write_text("appsettings.Local.json\n")
        (clone / "appsettings.Local.json").write_text("Ignored only in the main clone\n")
        (clone / "appsettings.Development.json").write_text("Not ignored anywhere\n")
        task = self.task(project)
        self.assertEqual((task / "repo/appsettings.Local.json").read_text(), "Ignored only in the main clone\n")
        self.assertFalse((task / "repo/appsettings.Development.json").exists())

    def test_worktreeinclude_selects_untracked_files_with_git_patterns(self):
        project = self.project()
        clone = project / "repo/main"
        (clone / ".git/info/exclude").write_text("cache/\n")
        (clone / ".worktreeinclude").write_text(
            "# Local files\n/config/**\n!config/excluded.txt\n/cache/\n!cache/\n/source.txt\n"
        )
        (clone / "config").mkdir()
        names = ("local.env", "file with spaces.txt", "line\nbreak.txt", "literal[1].txt")
        for name in (*names, "excluded.txt"):
            (clone / "config" / name).write_text(name)
        (clone / "cache").mkdir()
        (clone / "cache/ignored.txt").write_text("Ignored independently\n")
        (clone / "unselected.txt").write_text("Not selected\n")
        (clone / "source.txt").write_text("Uncommitted tracked content\n")
        task = self.task(project)
        for name in names:
            self.assertEqual((task / "repo/config" / name).read_text(), name)
        self.assertFalse((task / "repo/config/excluded.txt").exists())
        self.assertFalse((task / "repo/unselected.txt").exists())
        self.assertEqual((task / "repo/cache/ignored.txt").read_text(), "Ignored independently\n")
        self.assertEqual((task / "repo/source.txt").read_text(), "original\n")
        (task / "repo/config/local.env").write_text("Task value\n")
        (clone / "config/new.env").write_text("New local value\n")
        self.x_env("task", "fix-login", cwd=task)
        self.assertEqual((task / "repo/config/local.env").read_text(), "Task value\n")
        self.assertEqual((task / "repo/config/new.env").read_text(), "New local value\n")

    def test_worktreeinclude_preserves_deleted_tracked_task_file(self):
        project = self.project()
        clone = project / "repo/main"
        task = self.task(project)
        (clone / ".worktreeinclude").write_text("local.env\n")
        (clone / "local.env").write_text("Clone value\n")
        target = task / "repo/local.env"
        target.write_text("Tracked task value\n")
        self.git("-C", task / "repo", "add", "local.env")
        target.unlink()
        result = self.x_env("task", "fix-login", cwd=task)
        self.assertFalse(target.exists())
        self.assertIn("tracked in the task", result.stderr)

    def test_worktreeinclude_rejects_symlink_or_directory(self):
        project = self.project()
        clone = project / "repo/main"
        outside = self.root / "include-patterns"
        outside.write_text("*.env\n")
        include = clone / ".worktreeinclude"
        include.symlink_to(outside)
        self.assert_fails(self.x_env("task", "fix-login", cwd=project, check=False), "must be a regular file")
        include.unlink()
        include.mkdir()
        self.assert_fails(self.x_env("task", "fix-login", cwd=project, check=False), "must be a regular file")

    def test_settings_copy_does_not_restore_deleted_tracked_files(self):
        project = self.project()
        clone = project / "repo/main"
        (clone / ".git/info/exclude").write_text("appsettings*.json\n")
        task = self.task(project)
        target = task / "repo/appsettings.Local.json"
        target.write_text("Tracked task settings\n")
        self.git("-C", task / "repo", "add", "-f", "appsettings.Local.json")
        target.unlink()
        (clone / "appsettings.Local.json").write_text("Ignored clone settings\n")
        result = self.x_env("task", "fix-login", cwd=task)
        self.assertFalse(target.exists())
        self.assertIn("tracked in the task", result.stderr)

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
        self.x_env("task", "fix-login", cwd=task)
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
        result = self.x_env("task", "fix-login", cwd=task, check=False)
        self.assert_fails(result, "symbolic link")
        self.assertNotIn("Task ready", result.stderr)
        self.assertEqual(list(outside.iterdir()), [])

    def test_settings_copy_failure_can_retry_without_partial_destination(self):
        project = self.project()
        clone = project / "repo/main"
        (clone / ".git/info/exclude").write_text("appsettings*.json\n")
        content = "x" * (1 << 20)
        (clone / "appsettings.Local.json").write_text(content)

        def limit_file_size():
            resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 16, 1 << 16))

        result = self.x_env("task", "fix-login", cwd=project, check=False, preexec_fn=limit_file_size)
        self.assert_fails(result, "Could not copy local file")
        self.assertNotIn("Task ready", result.stderr)
        worktree = project / "tasks/fix-login/repo"
        self.assertFalse((worktree / "appsettings.Local.json").exists())
        self.assertEqual(list(worktree.glob(".x-env-copy-*")), [])
        self.x_env("task", "fix-login", cwd=project)
        self.assertEqual((worktree / "appsettings.Local.json").read_text(), content)


class DeleteTest(CliTest):
    def test_delete_removes_worktree_but_keeps_branch_records_and_other_tasks(self):
        project = self.project()
        task = self.task(project)
        other = self.task(project, "other")
        record = project / "sessions/fix-login/001-chief/session.json"
        record.parent.mkdir(parents=True)
        record.write_text("{}\n")
        result = self.x_env("delete", "fix-login", cwd=task / "repo")
        self.assertIn("Deleted task", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(task.exists())
        self.assertTrue((other / "repo/source.txt").is_file())
        worktrees = self.worktrees(project)
        self.assertNotIn(str(task / "repo"), worktrees)
        self.assertIn(str(other / "repo"), worktrees)
        self.assertTrue(self.has_ref(project / "repo/main", "refs/heads/feature/fix-login"))
        self.assertEqual(record.read_text(), "{}\n")

    def test_delete_requires_force_for_uncommitted_and_untracked_files(self):
        for kind in ("tracked", "untracked"):
            with self.subTest(kind=kind):
                project = self.project()
                task = self.task(project, kind)
                source = task / "repo" / ("source.txt" if kind == "tracked" else "new.txt")
                source.write_text("Keep this work\n")
                self.assert_fails(self.x_env("delete", kind, cwd=project, check=False), "--force")
                self.assertEqual(source.read_text(), "Keep this work\n")
                self.x_env("delete", kind, "--force", cwd=project)
                self.assertFalse(task.exists())

    def ignore_local_files(self, *patterns):
        (self.origin / ".gitignore").write_text("".join(f"{p}\n" for p in patterns))
        self.git("-C", self.origin, "add", ".gitignore")
        self.git("-C", self.origin, "commit", "-m", "Ignore local files")

    def test_delete_allows_unchanged_copied_files_and_other_ignored_files(self):
        self.ignore_local_files(".env", "build/")
        project = self.project()
        (project / "repo/main/.env").write_text("LOCAL_VALUE=1\n")
        task = self.task(project)
        (task / "repo/build").mkdir()
        (task / "repo/build/out.bin").write_text("Build output\n")
        self.assertEqual((task / "repo/.env").read_text(), "LOCAL_VALUE=1\n")
        self.x_env("delete", "fix-login", cwd=project)
        self.assertFalse(task.exists())

    def test_delete_requires_force_for_a_changed_copied_file(self):
        self.ignore_local_files(".env", "build/")
        project = self.project()
        (project / "repo/main/.env").write_text("LOCAL_VALUE=1\n")
        task = self.task(project)
        (task / "repo/.env").write_text("LOCAL_VALUE=2\n")
        (task / "repo/build").mkdir()
        (task / "repo/build/out.bin").write_text("Build output\n")
        result = self.x_env("delete", "fix-login", cwd=project, check=False)
        self.assert_fails(result, ".env")
        self.assertIn("Use --force to discard them.", result.stderr)
        self.assertNotIn("build", result.stderr)
        self.assertEqual((task / "repo/.env").read_text(), "LOCAL_VALUE=2\n")
        self.x_env("delete", "fix-login", "--force", cwd=project)
        self.assertFalse(task.exists())

    def test_delete_skips_a_copied_file_that_the_clone_no_longer_has(self):
        self.ignore_local_files(".env")
        project = self.project()
        (project / "repo/main/.env").write_text("LOCAL_VALUE=1\n")
        task = self.task(project)
        (project / "repo/main/.env").unlink()
        (task / "repo/.env").write_text("LOCAL_VALUE=2\n")
        self.x_env("delete", "fix-login", cwd=project)
        self.assertFalse(task.exists())

    def test_delete_detached_worktree_requires_force(self):
        project = self.project()
        task = self.task(project)
        self.git("-C", task / "repo", "checkout", "--detach")
        self.assert_fails(self.x_env("delete", "fix-login", cwd=project, check=False), "detached")
        self.x_env("delete", "fix-login", "--force", cwd=project)
        self.assertFalse(task.exists())

    def test_delete_allows_renamed_branch_and_preserves_it(self):
        project = self.project()
        task = self.task(project)
        self.git("-C", task / "repo", "branch", "-m", "renamed-task")
        self.x_env("delete", "fix-login", cwd=project)
        self.assertTrue(self.has_ref(project / "repo/main", "refs/heads/renamed-task"))

    def test_delete_force_removes_worktree_during_paused_rebase(self):
        project = self.project()
        repo = self.task(project) / "repo"
        (repo / "source.txt").write_text("Task commit\n")
        self.git("-C", repo, "commit", "-am", "Task change")
        branch_commit = self.out("-C", repo, "rev-parse", "HEAD")
        self.env["GIT_SEQUENCE_EDITOR"] = "sed -i 's/^pick /edit /'"
        self.git("-C", repo, "rebase", "-i", "HEAD~1")
        self.assertIn("rebase in progress", self.out("-C", repo, "status"))
        (repo / "source.txt").write_text("Uncommitted amendment\n")
        self.x_env("delete", "fix-login", "--force", cwd=project)
        self.assertFalse(repo.parent.exists())
        self.assertNotIn(str(repo), self.worktrees(project))
        self.assertEqual(self.out("-C", project / "repo/main", "rev-parse", "feature/fix-login"), branch_commit)

    def test_delete_removes_stale_worktree_registration(self):
        project = self.project()
        task = self.task(project)
        shutil.rmtree(task)
        self.x_env("delete", "fix-login", cwd=project)
        self.assertNotIn(str(task / "repo"), self.worktrees(project))

    def test_delete_preserves_task_when_git_worktree_removal_fails(self):
        project = self.project()
        task = self.task(project)
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
        self.assert_fails(self.x_env("delete", "fix-login", cwd=project, check=False), "Could not remove")
        self.assertTrue((task / "repo/source.txt").is_file())
        self.assertTrue((task / "AGENTS.md").is_file())
        wrapper.unlink()
        self.x_env("delete", "fix-login", cwd=project)
        self.assertFalse(task.exists())

    def test_delete_rejects_locked_worktree_even_with_force(self):
        project = self.project()
        task = self.task(project)
        self.git("-C", project / "repo/main", "worktree", "lock", task / "repo")
        self.assert_fails(self.x_env("delete", "fix-login", "--force", cwd=project, check=False), "locked")
        self.assertTrue((task / "repo/source.txt").is_file())

    def test_delete_rejects_locked_registration_without_a_worktree(self):
        project = self.project()
        task = self.task(project)
        self.git("-C", project / "repo/main", "worktree", "lock", task / "repo")
        shutil.rmtree(task / "repo")
        self.assert_fails(self.x_env("delete", "fix-login", "--force", cwd=project, check=False), "locked")
        self.assertTrue(task.exists())

    def test_delete_rejects_symlink_paths_even_with_force(self):
        for relative in ("tasks", "tasks/fix-login", "tasks/fix-login/repo"):
            with self.subTest(relative=relative):
                project = self.project()
                self.task(project)
                path = project / relative
                target = self.root / "outside"
                path.rename(target)
                path.symlink_to(target, target_is_directory=True)
                self.assert_fails(self.x_env("delete", "fix-login", "--force", cwd=project, check=False))
                self.assertTrue(target.is_dir())
                path.unlink()
                target.rename(path)

    def test_delete_rejects_worktree_from_another_repository(self):
        project = self.project()
        task = project / "tasks/fix-login"
        task.mkdir()
        self.git("-C", self.origin, "worktree", "add", "-b", "foreign", task / "repo")
        result = self.x_env("delete", "fix-login", "--force", cwd=project, check=False)
        self.assert_fails(result, "another repository")
        self.assertTrue((task / "repo/source.txt").is_file())

    def test_delete_retries_cleanup_without_worktree_or_task_directory(self):
        project = self.project()
        task = self.task(project)
        self.git("-C", project / "repo/main", "worktree", "remove", task / "repo")
        self.x_env("delete", "fix-login", cwd=project)
        self.assertFalse(task.exists())
        self.assert_fails(self.x_env("delete", "fix-login", cwd=project, check=False), "Task not found")

    def test_delete_rejects_invalid_arguments_before_deleting(self):
        project = self.project()
        task = self.task(project)
        for arguments in ((), ("../repo",), ("fix-login", "--unknown"), ("fix-login", "--force", "extra")):
            with self.subTest(arguments=arguments):
                self.assert_fails(self.x_env("delete", *arguments, cwd=project, check=False), code=2)
                self.assertTrue((task / "repo/source.txt").is_file())


if __name__ == "__main__":
    unittest.main()
