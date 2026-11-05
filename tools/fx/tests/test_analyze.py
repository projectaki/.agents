import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fx_analyze import inventory_task


class AnalyzeInventoryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="fx analysis ")
        self.addCleanup(self.temporary.cleanup)
        self.task = Path(self.temporary.name)
        self.session = self.task / "context/analyses/000001-analyze"
        self.session.mkdir(parents=True)

    def test_inventory_covers_full_logs_and_nested_reviews_without_loading_them_into_prompt(self):
        review = self.task / "context/groups/000001-review/1-codex/events"
        review.mkdir(parents=True)
        log = review / "native.jsonl"
        data = b'{"event":"earlier failure"}\n' * 10000 + b'{"event":"recovery"}'
        log.write_bytes(data)
        (self.task / "task.md").write_text("Goal\n")
        records = {record["path"]: record for record in inventory_task(self.task, self.session)["files"]}
        self.assertEqual(set(records), {"task.md", str(log.relative_to(self.task))})
        result = records[str(log.relative_to(self.task))]
        self.assertEqual(result["bytes"], len(data))
        self.assertEqual(result["lines"], 10001)
        self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())
        self.assertFalse(result["changed_during_inventory"])
        self.assertNotIn("earlier failure", str(records))

    def test_excludes_source_previous_analyses_and_symbolic_links(self):
        (self.task / "repo").mkdir()
        (self.task / "repo/source.txt").write_text("Current source")
        (self.session / "findings.md").write_text("Previous analysis")
        (self.task / "linked-file").symlink_to(self.task / "repo/source.txt")
        (self.task / "linked-directory").symlink_to(self.task / "repo", target_is_directory=True)
        result = inventory_task(self.task, self.session)
        self.assertEqual([record["path"] for record in result["files"]], ["linked-directory", "linked-file"])
        self.assertTrue(all(record["excluded"] == "Symbolic link." for record in result["files"]))
        self.assertIn("context/analyses/", result["excluded"])

    def test_inventory_includes_group_usage_and_price_snapshots_for_later_analysis(self):
        group = self.task / 'context/groups/000001-review'
        member = group / '1-agent-model'
        member.mkdir(parents=True)
        paths = [group / 'usage-summary.json', group / 'usage-summary.md',
                 member / 'usage.json', member / 'pricing.json']
        for path in paths:
            path.write_text('{}')
        records = inventory_task(self.task, self.session)['files']
        self.assertEqual({record['path'] for record in records},
                         {str(path.relative_to(self.task)) for path in paths})

    def test_records_read_errors_and_nonregular_files_without_blocking(self):
        unreadable = self.task / "unreadable.log"
        unreadable.write_text("event")
        os.mkfifo(self.task / "pipe")
        original_open = os.open

        def open_file(path, *args, **kwargs):
            if Path(path) == unreadable:
                raise PermissionError("Test read denial")
            return original_open(path, *args, **kwargs)

        with patch("fx_analyze.os.open", side_effect=open_file):
            records = {record["path"]: record for record in inventory_task(self.task, self.session)["files"]}
        self.assertIn("Test read denial", records["unreadable.log"]["error"])
        self.assertEqual(records["pipe"]["excluded"], "Not a regular file.")

    def test_rejects_session_outside_analysis_directory(self):
        with self.assertRaisesRegex(ValueError, "context/analyses"):
            inventory_task(self.task, self.task)

    def test_empty_files_have_zero_lines_and_valid_hash(self):
        (self.task / "empty.log").touch()
        record = inventory_task(self.task, self.session)["files"][0]
        self.assertEqual(record["lines"], 0)
        self.assertEqual(record["bytes"], 0)
        self.assertEqual(record["sha256"], hashlib.sha256(b"").hexdigest())


if __name__ == "__main__":
    unittest.main()
