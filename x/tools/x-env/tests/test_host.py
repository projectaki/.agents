"""`--host`: forwarding through Rex, with a fake `rex` on PATH (tests/fakes/rex).

In `-S` mode the fake runs the forwarded argv on this machine with stdout and
stderr mixed, as a Rex terminal shows them, so the remote side is the real
x-env, reached through the `~/.local/bin/x-env` link that `install` makes.
"""

import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from x_env import host

TOOL = Path(__file__).resolve().parents[1] / "x-env"
FAKES = Path(__file__).resolve().parent / "fakes"


class ProtocolTest(unittest.TestCase):
    def test_marked_stdout_and_unmarked_lines_split_back_apart(self):
        screen = io.StringIO()
        real_stdout = sys.stdout
        sys.stdout = screen
        try:
            with host.marked_stdout():
                print("/work/example")
                screen.write("x-env: Cloned.\nCloning into 'main'...\n")
                print("second\n", end="")
                print("no newline", end="")
        finally:
            sys.stdout = real_stdout
        self.assertEqual(
            host.split_output(screen.getvalue()),
            (["/work/example", "second", "no newline"], ["x-env: Cloned.", "Cloning into 'main'..."]),
        )


class ForwardTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="x-env host ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.home = self.root / "home"
        self.state = self.root / "rex"
        for folder in (self.home, self.state):
            folder.mkdir()
        self.env = {
            k: v for k, v in os.environ.items()
            if not k.startswith(("GIT_", "X_ENV_", "REX_")) and k not in ("BASH_ENV", "ENV", "CDPATH")
        }
        self.env.update(
            HOME=str(self.home),
            PATH=f"{self.home}/.local/bin:{FAKES}:{os.environ['PATH']}",
            X_ENV_ROOT=str(self.root / "work"),
            FAKE_REX_STATE=str(self.state),
            FAKE_REX_SERVER="1",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.invalid",
            GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="test@example.invalid",
        )
        self.origin = self.root / "origin"
        self.run_command("git", "init", "-q", "-b", "main", self.origin)
        self.run_command("git", "-C", self.origin, "commit", "-q", "--allow-empty", "-m", "Initial")

    def run_command(self, *arguments, check=True, **env):
        return subprocess.run([str(a) for a in arguments], cwd=self.root, env={**self.env, **env},
                              text=True, capture_output=True, check=check)

    def x_env(self, *arguments, check=True, **env):
        return self.run_command(TOOL, *arguments, check=check, **env)

    def install_on_host(self):
        self.x_env("install")

    def rex_calls(self):
        path = self.state / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def assert_session_closed(self):
        calls = self.rex_calls()
        [new] = [c for c in calls if c[3] == "new"]
        self.assertEqual(calls[-1], ["--autostart=false", "-S", "vps", "kill", "session:fake-1"])
        self.assertEqual((self.state / "session-1").read_text(), "killed")
        return new

    def test_sends_the_whole_command_without_host_to_x_env_on_the_host(self):
        self.install_on_host()
        self.x_env("--project", "example", "--host", "vps", "task", "fix", "--base=--host", check=False)
        new = self.assert_session_closed()
        self.assertEqual(new, [
            "--autostart=false", "-S", "vps", "new", "x-env task", "--keep-open", "--json", "--",
            "x-env", "--forwarded", "--project", "example", "task", "fix", "--base=--host",
        ])

    def test_remote_stdout_is_local_stdout_and_everything_else_is_stderr(self):
        self.install_on_host()
        result = self.x_env("--host=vps", "setup", "example", self.origin)
        project = self.root / "work/example"
        self.assertEqual(result.stdout, f"{project}\n")
        self.assertIn("Cloning into", result.stderr)  # git's own line, unmarked on the host
        self.assertTrue((project / "repo/main/.git").exists())
        self.assert_session_closed()

    def test_paths_are_resolved_on_the_host_from_its_home(self):
        self.install_on_host()
        (self.home / "origin").symlink_to(self.origin)
        result = self.x_env("--host", "vps", "setup", "example", "origin")
        self.assertEqual(result.stdout, f"{self.root / 'work/example'}\n")

    def test_remote_exit_status_and_error_pass_through(self):
        self.install_on_host()
        usage = self.x_env("--host", "vps", "--project", "example", "task", "bad.name", check=False)
        self.assertEqual((usage.returncode, usage.stdout), (2, ""))
        self.assertTrue(usage.stderr.startswith("x-env: "), usage.stderr)
        missing = self.x_env("--host", "vps", "--project", "nowhere", "task", "fix", check=False)
        self.assertEqual((missing.returncode, missing.stdout), (1, ""))
        self.assertIn("nowhere", missing.stderr)

    def test_missing_x_env_on_the_host_says_to_install_it(self):
        result = self.x_env("--host", "vps", "--project", "example", "task", "fix", check=False)
        self.assertEqual((result.returncode, result.stdout), (1, ""))
        self.assertIn("not installed on vps", result.stderr)
        self.assertIn("x-env install", result.stderr)
        self.assert_session_closed()

    def test_lost_transport_is_an_error_and_the_session_is_still_closed(self):
        self.install_on_host()
        result = self.x_env("--host", "vps", "setup", "example", self.origin, check=False, FAKE_REX_WAIT="lost")
        self.assertEqual((result.returncode, result.stdout), (1, ""))
        self.assertIn("result is unknown", result.stderr)
        self.assert_session_closed()

    def test_ctrl_c_closes_the_session(self):
        self.install_on_host()
        process = subprocess.Popen(
            [str(TOOL), "--host", "vps", "setup", "example", str(self.origin)], cwd=self.root,
            env={**self.env, "FAKE_REX_WAIT": "hang"}, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 20
        while not any(c[3] == "wait" for c in self.rex_calls()):
            self.assertLess(time.monotonic(), deadline, "the fake rex wait never started")
            time.sleep(0.05)
        process.send_signal(signal.SIGINT)
        stdout, _ = process.communicate(timeout=20)
        self.assertEqual((process.returncode, stdout), (130, ""))
        self.assert_session_closed()

    def test_install_and_shell_init_are_refused_with_host(self):
        for command in ("install", "shell-init"):
            with self.subTest(command=command):
                result = self.x_env("--host", "vps", command, check=False)
                self.assertEqual(result.returncode, 2)
                self.assertIn("without --host", result.stderr)
        self.assertEqual(self.rex_calls(), [])


if __name__ == "__main__":
    unittest.main()
