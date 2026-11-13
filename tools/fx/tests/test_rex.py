from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

import test_fx


REX = shutil.which("rex")


@unittest.skipUnless(REX, "Rex is required for terminal integration checks.")
class RexIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture = test_fx.FxTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        runtime = tempfile.TemporaryDirectory(prefix="fx-rex-")
        self.addCleanup(runtime.cleanup)
        socket = Path(runtime.name) / "rex.sock"
        self.endpoint = f"unix://{socket}"
        fixture.env.pop("FX_MULTIPLEXER")
        fixture.env.update(REX_SERVER=self.endpoint, SHELL="/bin/bash", FX_ORCHESTRATOR_AGENT="codex")
        self.server = subprocess.Popen(
            [REX, "server", "run", "--listen", self.endpoint, "--state-dir", runtime.name, "--restore=false"],
            env=fixture.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.addCleanup(self.stop_server)
        self.wait_for(socket.is_socket)
        self.project = fixture.project()
        self.task = self.project / "tasks/fix-login"
        self.launch = fixture.root / "launch.json"
        self.install_agent("codex", self.launch)

    def stop_server(self):
        if self.server.poll() is None:
            self.server.terminate()
            self.server.wait(timeout=5)

    def wait_for(self, predicate):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.05)
        self.fail("Rex did not reach the expected state.")

    def install_agent(self, agent, launch, keep_running=False):
        executable = self.fixture.bin / agent
        executable.write_text(f"""#!{sys.executable}
import json, os, sys, time
from pathlib import Path
if "--version" in sys.argv:
    print("test version")
    sys.exit(0)
session = os.environ.get("FX_SESSION_CONTEXT_DIR")
record = Path(session) / "test-launch.json" if session and {keep_running!r} else Path({str(launch)!r})
record.write_text(json.dumps({{"cwd": os.getcwd(), "tty": sys.stdin.isatty(),
                               "session": os.environ["REX_SESSION"], "args": sys.argv[1:]}}))
if session and {keep_running!r}:
    time.sleep(60)
""")

    def rex(self, *arguments):
        result = self.fixture.run_command(REX, "--server", self.endpoint, "--autostart=false", *arguments)
        return json.loads(result.stdout)

    def sessions(self):
        return self.rex("session", "ls", "--json")["sessions"]

    def open_task(self):
        result = self.fixture.fx("task", "fix-login", cwd=self.project)
        record = json.loads((self.task / ".fx-terminal.json").read_text())
        self.assertEqual(record["backend"], "rex")
        self.assertIn(record["name"], result.stderr)
        self.wait_for(self.launch.exists)
        return record

    def test_task_reopens_agent_tab_and_deletes_owned_session(self):
        record = self.open_task()
        session = record["id"]
        launch = json.loads(self.launch.read_text())
        self.assertTrue(launch["tty"])
        self.assertEqual(launch["cwd"], str(self.task))
        self.assertEqual(launch["session"], session)

        self.fixture.env["FX_MULTIPLEXER"] = "zellij"
        self.fixture.fx("task", "fix-login", cwd=self.project)
        self.assertEqual([entry["session_id"] for entry in self.sessions()], [session])

        self.launch.unlink()
        self.fixture.env.update(REX_SESSION=session, REX_BLOCK="block:unused")
        self.fixture.fx("agent", "codex", "--name", "review", "--new-tab",
                        "--prompt", "Check quotes: ' \" $value", cwd=self.task)
        self.wait_for(self.launch.exists)
        agent = json.loads(self.launch.read_text())
        self.assertEqual(agent["session"], session)
        self.assertTrue(agent["tty"])
        self.assertIn("Check quotes: ' \" $value", agent["args"][-1])

        result = self.fixture.fx("delete", "fix-login", cwd=self.project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.task / "repo").exists())

        for key in ("REX_SESSION", "REX_BLOCK"):
            del self.fixture.env[key]
        self.fixture.fx("delete", "fix-login", cwd=self.project)
        self.assertEqual(self.sessions(), [])
        self.assertFalse(self.task.exists())

    def test_task_and_agent_tab_work_with_rex_without_interactive_flag(self):
        executable = self.fixture.bin / "rex"
        executable.write_text(f"""#!{sys.executable}
import os, subprocess, sys
arguments = sys.argv[1:]
options = arguments[:arguments.index("--")] if "--" in arguments else arguments
if "--interactive" in options:
    sys.exit("Error: unknown flag: --interactive")
if "--help" in options:
    result = subprocess.run([{REX!r}, *arguments], text=True, capture_output=True)
    sys.stdout.write("".join(line for line in result.stdout.splitlines(keepends=True)
                             if "--interactive" not in line))
    sys.stderr.write(result.stderr)
    sys.exit(result.returncode)
os.execv({REX!r}, [{REX!r}, *arguments])
""")
        executable.chmod(0o755)

        result = self.fixture.fx("task", "fix-login", cwd=self.project, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads((self.task / ".fx-terminal.json").read_text())
        self.assertEqual(record["backend"], "rex")
        self.wait_for(self.launch.exists)
        self.assertTrue(json.loads(self.launch.read_text())["tty"])

        self.launch.unlink()
        self.fixture.env.update(REX_SESSION=record["id"], REX_BLOCK="block:unused")
        prompt = "Check literal arguments: --interactive, 'quotes', and $value"
        result = self.fixture.fx("agent", "codex", "--name", "review", "--new-tab",
                                 "--prompt", prompt, cwd=self.task, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.wait_for(self.launch.exists)
        launch = json.loads(self.launch.read_text())
        self.assertTrue(launch["tty"])
        self.assertEqual(launch["session"], record["id"])
        self.assertIn(prompt, launch["args"][-1])
        self.assertEqual(len(self.sessions()), 1)

    def test_concurrent_reopens_create_one_session(self):
        self.fixture.task(self.project)
        with ThreadPoolExecutor(max_workers=2) as executor:
            requests = [executor.submit(self.fixture.fx, "task", "fix-login", cwd=self.project)
                        for _ in range(2)]
            for request in requests:
                request.result()
        self.assertEqual(len(self.sessions()), 1)

    def test_background_review_opens_a_rex_window(self):
        self.fixture.review_repository(self.project / "repo/main")
        self.install_agent("claude", self.launch)
        result = self.fixture.fx("pr", "review", "17", cwd=self.project)
        workspace, = (self.project / "reviews/pr-17").iterdir()
        self.wait_for(self.launch.exists)
        launch = json.loads(self.launch.read_text())
        self.assertEqual(launch["cwd"], str(workspace))
        self.assertTrue(launch["tty"])
        self.assertIn(launch["session"], result.stdout)

    def test_group_interrupt_stops_interactive_members(self):
        self.install_agent("codex", self.launch, keep_running=True)
        record = self.open_task()
        self.fixture.env.update(REX_SESSION=record["id"], REX_BLOCK="block:unused")
        self.fixture.fx("agent", "group", "--interactive", "--name", "review",
                        "--agent", "codex", "--prompt", "Review source", cwd=self.task)
        group, = (self.task / "context/groups").iterdir()
        member, = group.glob("1-codex-*")
        self.wait_for((member / "test-launch.json").exists)
        run_state = group / "run-state.json"
        state = json.loads(run_state.read_text())
        os.kill(state["runner_pid"], signal.SIGINT)
        self.wait_for(lambda: json.loads(run_state.read_text())["status"] == "failed")
        self.assertEqual(json.loads(run_state.read_text())["members"][member.name]["status"], "cancelled")

    def test_unreachable_saved_rex_session_keeps_the_worktree(self):
        self.open_task()
        self.stop_server()
        for arguments in (("task", "fix-login"), ("delete", "fix-login")):
            result = self.fixture.fx(*arguments, cwd=self.project, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Reconnect Rex", result.stderr)
            self.assertTrue((self.task / "repo/source.txt").exists())

    def test_explicit_rex_reports_unavailability_without_using_zellij(self):
        self.stop_server()
        self.fixture.env["FX_MULTIPLEXER"] = "rex"
        result = self.fixture.fx("task", "fix-login", cwd=self.project, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No terminal backend is available (rex)", result.stderr)
        self.assertFalse((self.task / ".fx-terminal.json").exists())

    def test_auto_falls_back_to_zellij_when_rex_is_unreachable(self):
        self.stop_server()
        result = self.fixture.fx("task", "fix-login", cwd=self.project)
        record = json.loads((self.task / ".fx-terminal.json").read_text())
        self.assertEqual(record["backend"], "zellij")
        self.assertIn("example-fix-login", result.stdout)


if __name__ == "__main__":
    unittest.main()
