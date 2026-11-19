"""`x-env install`, run through the CLI with a fake HOME."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "x-env"
UBUNTU_PROFILE = '''# ~/.profile
if [ -d "$HOME/.local/bin" ] ; then
    PATH="$HOME/.local/bin:$PATH"
fi
'''


class InstallTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="x-env install ")
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name).resolve()
        self.link = self.home / ".local/bin/x-env"
        self.env = {"HOME": str(self.home), "PATH": "/usr/bin:/bin"}

    def install(self, check=True):
        return subprocess.run([str(TOOL), "install"], env=self.env, text=True, capture_output=True, check=check)

    def files(self):
        return {name: (self.home / name).read_text() for name in (".bashrc", ".profile")}

    def shell(self, *flags, script):
        """A clean bash with only HOME and a minimal PATH, as a new login."""
        return subprocess.run(["bash", *flags, "-c", script], env=self.env, cwd=self.home,
                              text=True, capture_output=True, stdin=subprocess.DEVNULL)

    def test_fresh_home_gets_a_command_in_login_and_interactive_shells(self):
        result = self.install()
        self.assertEqual(result.stdout, "")
        self.assertEqual(len(result.stderr.splitlines()), 3, result.stderr)
        self.assertEqual(self.link.resolve(), TOOL.resolve())
        login = self.shell("-l", script="command -v x-env")
        self.assertEqual(login.stdout.strip(), str(self.link))
        interactive = self.shell("-i", script="type -t x-env")
        self.assertEqual(interactive.stdout.strip(), "function")

    def test_second_run_changes_nothing_and_prints_nothing(self):
        self.install()
        before = self.files()
        result = self.install()
        self.assertEqual((result.stdout, result.stderr), ("", ""))
        self.assertEqual(self.files(), before)
        self.assertEqual(self.files()[".bashrc"].count("# >>> x-env >>>"), 1)

    def test_link_to_another_version_is_replaced(self):
        self.link.parent.mkdir(parents=True)
        self.link.symlink_to("/old/plugin/1.0.0/tools/x-env/x-env")
        result = self.install()
        self.assertEqual(self.link.resolve(), TOOL.resolve())
        self.assertIn("/old/plugin/1.0.0", result.stderr)
        self.assertEqual([p.name for p in self.link.parent.iterdir()], ["x-env"])  # no temporary left

    def test_regular_file_is_refused_and_kept(self):
        self.link.parent.mkdir(parents=True)
        self.link.write_text("#!/bin/sh\necho mine\n")
        result = self.install(check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not a symbolic link", result.stderr)
        self.assertEqual(self.link.read_text(), "#!/bin/sh\necho mine\n")

    def test_existing_profile_line_is_kept_without_a_block(self):
        (self.home / ".profile").write_text(UBUNTU_PROFILE)
        result = self.install()
        self.assertEqual((self.home / ".profile").read_text(), UBUNTU_PROFILE)
        self.assertNotIn(".profile", result.stderr)
        self.assertEqual(self.shell("-l", script="command -v x-env").stdout.strip(), str(self.link))

    def test_existing_files_keep_their_content_and_an_old_block_is_updated(self):
        (self.home / ".bashrc").write_text("alias ll='ls -l'\n# >>> x-env >>>\nold line\n# <<< x-env <<<\nexport A=1")
        result = self.install()
        bashrc = (self.home / ".bashrc").read_text()
        self.assertTrue(bashrc.startswith("alias ll='ls -l'\n# >>> x-env >>>\n"))
        self.assertTrue(bashrc.endswith("# <<< x-env <<<\nexport A=1"))
        self.assertNotIn("old line", bashrc)
        self.assertIn("Updated", result.stderr)

    def test_install_through_the_link_keeps_the_link(self):
        self.install()
        result = subprocess.run([str(self.link), "install"], env=self.env, text=True, capture_output=True)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        self.assertEqual(self.link.resolve(), TOOL.resolve())


if __name__ == "__main__":
    unittest.main()
