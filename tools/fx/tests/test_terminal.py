import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fx_terminal import backend_order, current_terminal, saved_terminal
from terminals import rex


class TerminalSelectionTest(unittest.TestCase):
    def test_default_and_explicit_backend_order(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(backend_order(), ("rex", "zellij"))
        for backend in ("rex", "zellij"):
            with self.subTest(backend=backend), patch.dict(os.environ, FX_MULTIPLEXER=backend):
                self.assertEqual(backend_order(), (backend,))
        with patch.dict(os.environ, FX_MULTIPLEXER="invalid"):
            with self.assertRaisesRegex(ValueError, "FX_MULTIPLEXER"):
                backend_order()

    def test_nested_zellij_uses_the_current_zellij_session(self):
        with patch.dict(os.environ, {"ZELLIJ": "0", "ZELLIJ_SESSION_NAME": "task",
                                     "REX_SESSION": "session:parent", "REX_BLOCK": "block:parent"}, clear=True):
            self.assertEqual(current_terminal(), ("zellij", "task"))

    def test_background_review_uses_its_own_session(self):
        with patch.dict(os.environ, {"FX_TERMINAL_BACKEND": "rex", "FX_TERMINAL_SESSION": "session:review",
                                     "ZELLIJ": "0", "ZELLIJ_SESSION_NAME": "caller"}, clear=True):
            self.assertEqual(current_terminal(), ("rex", "session:review"))

    def test_rex_does_not_pass_a_remote_server_target(self):
        with patch.dict(os.environ, REX_SERVER="https://another-machine.example"):
            self.assertNotIn("--server", rex.command("whoami"))
            self.assertNotIn("REX_SERVER", rex.environment())

    def test_rex_shows_session_in_the_only_connected_app(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("terminals.rex.subprocess.run") as run:
                def reply(command, **options):
                    stdout = '{"clients": [{"client_id": "client:mac"}]}' if "--json" in command else "client:mac\n"
                    return subprocess.CompletedProcess(command, 0, stdout, "")
                run.side_effect = reply
                rex.show(Path("/tmp/workspace"), "task", "session:task")
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[0][-4:], ["client", "ls", "--quiet", "--short=false"])
        self.assertEqual(commands[1][-5:],
                         ["--client", "client:mac", "do", "session.select", "session_id=session:task"])

    def test_rex_prints_manual_hint_when_app_selection_is_ambiguous(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("terminals.rex.subprocess.run") as run, patch("sys.stderr") as stderr:
                run.return_value.stdout = "client:mac\nclient:phone\n"
                run.return_value.returncode = 0
                rex.show(Path("/tmp/workspace"), "task", "session:task")
        run.assert_called_once()
        stderr.write.assert_any_call("Open Rex session task (session:task) on this host.")

    def test_rex_uses_an_explicit_client_without_listing_apps(self):
        with patch.dict(os.environ, {"REX_CLIENT": "mac"}, clear=True):
            with patch("terminals.rex.subprocess.run") as run:
                run.return_value.returncode = 0
                rex.show(Path("/tmp/workspace"), "task", "session:task")
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][-5:],
                         ["--client", "mac", "do", "session.select", "session_id=session:task"])

    def test_rex_label_distinguishes_workspaces_and_fits_the_server_limit(self):
        name = "project-task" * 20
        first = rex.label(Path("/tmp/first"), name)
        second = rex.label(Path("/tmp/second"), name)
        self.assertNotEqual(first, second)
        self.assertLessEqual(len(first), 128)
        self.assertEqual(first, rex.label(Path("/tmp/first"), name))

    def test_saved_terminal_rejects_unknown_backends(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / ".fx-terminal.json").write_text('{"backend": "unknown", "name": "task"}')
            with self.assertRaisesRegex(ValueError, "Invalid terminal session record"):
                saved_terminal(workspace)


if __name__ == "__main__":
    unittest.main()
