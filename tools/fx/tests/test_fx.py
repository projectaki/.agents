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
        self.assertEqual(branch.stdout.strip(), "codex/second")

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
            self.assertEqual(branch, f"codex/{name}")
        branch = self.run_command("git", "-C", clone, "branch", "--show-current").stdout.strip()
        self.assertEqual(branch, "main")

    def test_task_reattaches_existing_branch(self):
        project = self.project()
        self.run_command("git", "-C", project / "repo/main", "branch", "codex/fix-login")
        self.assertTrue((self.task(project) / "repo/.git").is_file())

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
        self.assertNotEqual(upstream.returncode, 0)

    def test_new_task_supports_a_default_branch_not_named_main(self):
        self.run_command("git", "-C", self.origin, "branch", "-m", "trunk")
        project = self.project()
        result = self.fx("task", "fix-login", "--no-attach", cwd=project)
        self.assertIn("refs/remotes/origin/trunk", result.stderr)
        self.assertTrue((Path(result.stdout.strip()) / "repo/.git").is_file())

    def test_explicit_base_prefers_local_branch_and_supports_remote_branches(self):
        self.run_command("git", "-C", self.origin, "switch", "-c", "develop")
        (self.origin / "source.txt").write_text("Remote development\n")
        self.run_command("git", "-C", self.origin, "commit", "-am", "Development change")
        self.run_command("git", "-C", self.origin, "branch", "release")
        self.run_command("git", "-C", self.origin, "switch", "main")
        project = self.project()
        self.run_command("git", "-C", project / "repo/main", "branch", "develop", "main")
        for name, base, expected in (
            ("local", "develop", "original\n"),
            ("remote", "origin/develop", "Remote development\n"),
            ("remote-fallback", "release", "Remote development\n"),
        ):
            with self.subTest(base=base):
                result = self.fx("task", name, "--base", base, "--no-attach", cwd=project)
                task = Path(result.stdout.strip())
                self.assertEqual((task / "repo/source.txt").read_text(), expected)

    def test_unknown_default_requires_an_explicit_base(self):
        project = self.project()
        self.run_command("git", "-C", project / "repo/main", "remote", "set-head", "origin", "--delete")
        result = self.fx("task", "fix-login", "--no-attach", cwd=project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Supply --base", result.stderr)
        result = self.fx("task", "fix-login", "--base", "main", "--no-attach", cwd=project)
        self.assertTrue((Path(result.stdout.strip()) / "repo/.git").is_file())

    def test_new_tasks_do_not_fetch(self):
        project = self.project()
        (self.origin / "source.txt").write_text("Not fetched\n")
        self.run_command("git", "-C", self.origin, "commit", "-am", "Unfetched change")
        task = self.task(project)
        self.assertEqual((task / "repo/source.txt").read_text(), "original\n")

    def test_reopening_task_with_base_preserves_existing_changes(self):
        project = self.project()
        task = self.task(project)
        (task / "repo/source.txt").write_text("Preserved changes\n")
        result = self.fx("task", "fix-login", "--base", "different-branch", "--no-attach", cwd=project)
        self.assertIn("--base does not change", result.stderr)
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
                branch = self.run_command("git", "-C", clone, "show-ref", "--verify", "refs/heads/codex/invalid-base", check=False)
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
                        self.assertEqual(arguments[8:], ["--add-dir", str(project / "project_context")])

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

    def test_commands_require_the_correct_working_directory(self):
        project = self.project()
        self.assertNotEqual(self.fx("task", "fix", check=False).returncode, 0)
        self.assertNotEqual(self.fx("agent", "claude", cwd=project, check=False).returncode, 0)

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
