import concurrent.futures
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fx_session import create_session_directory


class SessionDirectoryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.task = Path(self.temporary.name)
        self.context = self.task / "context"
        self.context.mkdir()

    def create(self, name="investigate-model", parent=None):
        return create_session_directory(self.task, parent or self.context, name)

    def test_sequence_is_shared_across_names_and_parent_directories(self):
        first = self.create()
        groups = self.context / "groups"
        groups.mkdir()
        group = self.create("review", groups)
        comparisons = group / "comparisons"
        comparisons.mkdir()
        comparison = self.create("summary-model", comparisons)
        last = self.create("implement-other-model")
        self.assertEqual([path.name for path in (first, group, comparison, last)], [
            "000001-investigate-model", "000002-review", "000003-summary-model",
            "000004-implement-other-model",
        ])
        self.assertEqual(first.stat().st_mode & 0o777, 0o700)

    def test_parallel_allocations_have_distinct_ordered_numbers(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            paths = list(pool.map(lambda index: self.create(f"review-{index}-model"), range(12)))
        self.assertEqual(sorted(int(path.name.split("-", 1)[0]) for path in paths), list(range(1, 13)))
        self.assertTrue(all(path.is_dir() for path in paths))
        self.assertTrue(sorted(path.name for path in paths)[-1].startswith("000012-"))

    def test_deleted_session_does_not_reuse_its_number(self):
        self.create().rmdir()
        self.assertEqual(self.create().name, "000002-investigate-model")

    def test_task_sequences_are_independent(self):
        self.create()
        other = self.task / "other-task"
        context = other / "context"
        context.mkdir(parents=True)
        self.assertEqual(create_session_directory(other, context, "review-model").name,
                         "000001-review-model")

    def test_existing_destination_is_preserved(self):
        existing = self.context / "000001-investigate-model"
        existing.mkdir()
        (existing / "findings.md").write_text("Keep evidence")
        self.assertEqual(self.create().name, "000002-investigate-model")
        self.assertEqual((existing / "findings.md").read_text(), "Keep evidence")

    def test_failed_directory_creation_reserves_number(self):
        with patch("fx_session.Path.mkdir", side_effect=PermissionError("Cannot create directory")):
            with self.assertRaisesRegex(PermissionError, "Cannot create"):
                self.create()
        self.assertEqual(self.create().name, "000002-investigate-model")

    def test_invalid_names_do_not_allocate_numbers(self):
        for name in ("", "../escape", "two words", "-model", "model\nnext"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.create(name)
        self.assertFalse((self.task / ".fx-session-sequence").exists())

    def test_corrupt_sequence_is_preserved_and_rejected(self):
        sequence = self.task / ".fx-session-sequence"
        for value in ("bad", "-1", "1\n2"):
            with self.subTest(value=value):
                sequence.write_text(value)
                with self.assertRaisesRegex(ValueError, "Invalid task session sequence"):
                    self.create()
                self.assertEqual(sequence.read_text(), value)
        self.assertEqual(list(self.context.iterdir()), [])

    def test_sequence_symlink_is_rejected_without_changing_target(self):
        target = self.task / "keep.txt"
        target.write_text("Keep this")
        (self.task / ".fx-session-sequence").symlink_to(target)
        with self.assertRaises(OSError):
            self.create()
        self.assertEqual(target.read_text(), "Keep this")

    def test_parent_outside_context_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "inside the task context"):
            self.create(parent=self.task)
        self.assertFalse((self.task / ".fx-session-sequence").exists())


if __name__ == "__main__":
    unittest.main()
