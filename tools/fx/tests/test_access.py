import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agents"))
from fx_access import resolve_access, saved_access, session_access, validate_access
from claude_access import configure_settings, permission_mode
from codex_access import access_arguments


class AccessTest(unittest.TestCase):
    def test_access_validation(self):
        for mode in ("auto", "full"):
            self.assertEqual(validate_access(mode), mode)
        for mode in ("", "AUTO", "--full", "full\n", None):
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, "auto or full"):
                validate_access(mode)

    def test_explicit_then_saved_then_environment_then_auto(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_access(directory=directory), "auto")
            os.environ["FX_ACCESS"] = "full"
            self.assertEqual(resolve_access(directory=directory), "full")
            self.assertEqual(session_access(directory), "auto")
            (Path(directory) / "access.txt").write_text("auto\n")
            self.assertEqual(resolve_access(directory=directory), "auto")
            self.assertEqual(resolve_access("full", directory), "full")
            os.environ["FX_ACCESS"] = "invalid"
            self.assertEqual(resolve_access("auto"), "auto")
            with self.assertRaises(ValueError):
                resolve_access()

    def test_invalid_saved_access_never_falls_back_to_full(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, FX_ACCESS="full"):
            path = Path(directory) / "access.txt"
            path.write_text("invalid")
            with self.assertRaises(ValueError):
                resolve_access(directory=directory)
            path.unlink()
            path.symlink_to(Path(directory) / "missing")
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                saved_access(directory)

    def test_provider_access_arguments(self):
        self.assertEqual(permission_mode("auto"), "auto")
        self.assertEqual(permission_mode("full"), "bypassPermissions")
        self.assertEqual(access_arguments("auto"), ["--approve-for-me"])
        self.assertEqual(access_arguments("full"), ["--dangerously-bypass-approvals-and-sandbox"])
        for function in (permission_mode, access_arguments):
            with self.assertRaises(ValueError):
                function("invalid")

    def test_claude_auto_restores_sandbox_configuration_and_preserves_other_settings(self):
        for settings, expected in (
            ({"hooks": {}}, {"hooks": {}}),
            ({"sandbox": {"enabled": False}}, {}),
            ({"sandbox": {"enabled": True}}, {"sandbox": {"enabled": True}}),
            ({"hooks": {}, "sandbox": {"enabled": False, "network": {}}},
             {"hooks": {}, "sandbox": {"network": {}}}),
        ):
            with self.subTest(settings=settings):
                self.assertEqual(configure_settings(settings, "auto"), expected)
        settings = {"hooks": {}, "sandbox": {"enabled": True, "network": {}}}
        self.assertEqual(configure_settings(settings, "full"),
                         {"hooks": {}, "sandbox": {"enabled": False, "network": {}}})
        for settings in ([], {"sandbox": None}):
            with self.assertRaises(ValueError):
                configure_settings(settings, "auto")


if __name__ == "__main__":
    unittest.main()
