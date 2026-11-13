import os
from pathlib import Path
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
        clients = {"clients": [
            {"client_id": "app", "info": {"kind": "app"}, "connection_state": "connected"},
            {"client_id": "cli", "info": {"kind": "cli"}, "connection_state": "connected"},
        ]}
        with patch.dict(os.environ, {}, clear=True):
            with patch("terminals.rex.request", return_value=clients):
                with patch("terminals.rex.subprocess.run") as action:
                    action.return_value.returncode = 0
                    rex.show(Path("/tmp/workspace"), "task", "session:task")
        self.assertEqual(action.call_args.args[0][-5:],
                         ["--client", "app", "do", "session.select", "session_id=session:task"])

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
