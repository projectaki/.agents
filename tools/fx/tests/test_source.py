import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fx_source import source_identity


class SourceTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repository = Path(temporary.name)
        self.git("init", "-q")
        self.source = self.repository / "source.txt"
        self.source.write_text("original")
        (self.repository / ".gitignore").write_text("output/\n")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Initial source")

    def git(self, *arguments):
        return subprocess.run(["git", "-C", str(self.repository), *arguments],
                              capture_output=True, text=True, check=True).stdout.strip()

    def test_dirty_content_changes_with_the_same_commit_and_dirty_status(self):
        self.source.write_text("first edit")
        first = source_identity(self.repository)
        status = self.git("status", "--porcelain")
        self.source.write_text("later edit")
        second = source_identity(self.repository)
        self.assertEqual(first["revision"], second["revision"])
        self.assertEqual(status, self.git("status", "--porcelain"))
        self.assertNotEqual(first["content_sha256"], second["content_sha256"])

    def test_untracked_files_and_deletions_change_identity_but_ignored_output_does_not(self):
        original = source_identity(self.repository)
        output = self.repository / "output"
        output.mkdir()
        (output / "build").write_text("generated")
        self.assertEqual(original, source_identity(self.repository))
        extra = self.repository / "new.txt"
        extra.write_text("new source")
        self.assertNotEqual(original, source_identity(self.repository))
        extra.unlink()
        self.assertEqual(original, source_identity(self.repository))
        self.source.unlink()
        self.assertNotEqual(original, source_identity(self.repository))

    def test_names_modes_and_symlinks_affect_identity(self):
        first = source_identity(self.repository)
        self.source.chmod(0o755)
        executable = source_identity(self.repository)
        self.assertNotEqual(first, executable)
        self.source.rename(self.repository / "renamed.txt")
        self.assertNotEqual(executable, source_identity(self.repository))
        link = self.repository / "link"
        link.symlink_to("missing-one")
        one = source_identity(self.repository)
        link.unlink()
        link.symlink_to("missing-two")
        self.assertNotEqual(one, source_identity(self.repository))

    def test_unavailable_repository_and_special_file_do_not_claim_identity(self):
        self.assertIsNone(source_identity(self.repository / "missing")["content_sha256"])
        self.source.unlink()
        os.mkfifo(self.source)
        self.assertIsNone(source_identity(self.repository)["content_sha256"])

    def test_hashing_failure_does_not_claim_identity(self):
        with patch("fx_source.Path.open", side_effect=OSError("unreadable")):
            self.assertIsNone(source_identity(self.repository)["content_sha256"])

    def test_identity_time_limit_does_not_claim_identity(self):
        with patch("fx_source.time.monotonic", side_effect=[0, 11]):
            self.assertIsNone(source_identity(self.repository)["content_sha256"])

    def test_edit_while_hashing_does_not_claim_a_stable_identity(self):
        original_open = Path.open

        def edit_at_read(path, mode="r", *args, **kwargs):
            if path == self.source and mode == "rb":
                with original_open(path, "w") as stream:
                    stream.write("source changed while recording")
            return original_open(path, mode, *args, **kwargs)

        with patch("fx_source.Path.open", new=edit_at_read):
            self.assertIsNone(source_identity(self.repository)["content_sha256"])


if __name__ == "__main__":
    unittest.main()
