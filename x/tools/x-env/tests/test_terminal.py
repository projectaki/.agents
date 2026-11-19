"""Terminal detection, with a fake `rex` on PATH (tests/fakes/rex)."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from x_env import terminal

FAKES = Path(__file__).resolve().parent / "fakes"


class DetectTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.state = Path(temporary.name)
        self.empty_bin = self.state / "empty-bin"
        self.empty_bin.mkdir()

    def detect(self, path, server):
        env = {"PATH": path, "FAKE_REX_STATE": str(self.state), "FAKE_REX_SERVER": server}
        with mock.patch.dict(os.environ, env):
            return terminal.detect()

    def test_reachable_server_gives_rex(self):
        found = self.detect(f"{FAKES}:{os.environ['PATH']}", server="1")
        self.assertEqual((found.name, found.visible), ("rex", True))

    def test_no_server_gives_no_terminal(self):
        found = self.detect(f"{FAKES}:{os.environ['PATH']}", server="0")
        self.assertEqual((found.name, found.visible), ("none", False))

    def test_no_rex_executable_gives_no_terminal(self):
        found = self.detect(str(self.empty_bin), server="1")
        self.assertEqual((found.name, found.visible), ("none", False))

    def test_detection_never_starts_a_server(self):
        self.detect(f"{FAKES}:{os.environ['PATH']}", server="0")
        self.assertTrue((self.state / "calls.jsonl").exists())  # the fake was called
        self.assertFalse((self.state / "server-started").exists())


if __name__ == "__main__":
    unittest.main()
