"""Config: defaults, `[this]` from the file, and rejected values."""

import socket
import tempfile
import unittest
from pathlib import Path

from x_env import config
from x_env.model import Access, XEnvError


class LoadTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)

    def write(self, text):
        path = config.config_file(self.home)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_defaults_without_a_file(self):
        loaded = config.load({}, self.home)
        self.assertEqual(loaded.root, self.home / "work")
        self.assertEqual(loaded.host, socket.gethostname())
        self.assertIs(loaded.access, Access.AUTO)

    def test_this_table_sets_host_and_access(self):
        self.write('[this]\nhost = "vps"\naccess = "full"\n')
        loaded = config.load({"X_ENV_ROOT": "/srv/work"}, self.home)
        self.assertEqual((loaded.root, loaded.host, loaded.access), (Path("/srv/work"), "vps", Access.FULL))

    def test_rejects_unknown_access(self):
        self.write('[this]\naccess = "yolo"\n')
        with self.assertRaises(XEnvError):
            config.load({}, self.home)

    def test_rejects_invalid_toml(self):
        self.write("[this\n")
        with self.assertRaises(XEnvError):
            config.load({}, self.home)

    def test_rejects_empty_host(self):
        self.write('[this]\nhost = ""\n')
        with self.assertRaises(XEnvError):
            config.load({}, self.home)


if __name__ == "__main__":
    unittest.main()
