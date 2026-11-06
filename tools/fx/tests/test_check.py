import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fx_check import check_records, freshness
from fx_context import prepare_context, save_response


TOOL = Path(__file__).resolve().parents[1] / "fx"


class CheckTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.env = {
            **os.environ, "HOME": str(root), "FX_ROOT": str(root / "projects"),
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
        }
        self.env.pop("FX_SESSION_CONTEXT_DIR", None)
        origin = root / "origin"
        subprocess.run(["git", "init", "-qb", "main", origin], check=True, env=self.env)
        (origin / "source.txt").write_text("original")
        subprocess.run(["git", "-C", origin, "add", "."], check=True, env=self.env)
        subprocess.run(["git", "-C", origin, "-c", "user.name=Test",
                        "-c", "user.email=test@example.invalid", "commit", "-qm", "Initial"],
                       check=True, env=self.env)
        project = subprocess.check_output([TOOL, "setup", "example", origin],
                                          env=self.env, text=True, stderr=subprocess.PIPE).strip()
        self.task = Path(subprocess.check_output([TOOL, "task", "example", "--no-attach"],
                                                cwd=project, env=self.env, text=True,
                                                stderr=subprocess.PIPE).strip())
        self.repo = self.task / "repo"
        self.context = self.task / "context"
        self.implementation = self.create_session("session-implementation")
        self.reviewer = self.create_session("session-review")

    def create_session(self, name):
        session = self.context / name
        session.mkdir()
        (session / "instructions.md").touch()
        (session / "handoff.md").write_text("Current handoff")
        return session

    def check(self, *args, expected=0):
        result = subprocess.run([TOOL, "task", "check", *args], cwd=self.repo,
                                env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, expected, result.stderr)
        return result.stdout

    def save(self, session, turn, response):
        return save_response(session, "test-agent", session.name, turn, response)

    def test_passing_check_survives_later_unrelated_response_and_failed_review_rerun(self):
        self.check("--session", self.implementation, "--", "sh", "-c", "exit 7", expected=7)
        blocked = self.save(self.implementation, "one", "Tests blocked.")
        self.check("--session", self.implementation, "--", "sh", "-c", "echo 'tests passed'")
        latest = self.save(self.implementation, "two", "Updated project memory.")
        self.check("--session", self.reviewer, "--", "sh", "-c", "exit 8", expected=8)
        review = self.save(self.reviewer, "one", "Rerun failed.")

        for path, outcomes in ((blocked, ["failed"]), (latest, ["failed", "passed"]),
                               (review, ["failed"])):
            records = json.loads((path / "checks.json").read_text())
            self.assertEqual([record["result"] for record in records], outcomes)
        self.assertIn("tests passed", (self.task / check_records(self.context)[1]["evidence"]).read_text())
        for sources, include_responses in (([], True), ([latest], True), ([latest], False)):
            context = prepare_context(self.task, sources, include_responses=include_responses)
            for filename in ("checks.json", "metadata.json", "handoff.md"):
                self.assertIn(str((latest / filename).relative_to(self.task)), context)
        self.assertIn("passed (current)", self.check("status"))
        (self.repo / "source.txt").write_text("changed")
        self.assertIn("passed (historical)", self.check("status"))
        self.check("--", "true")
        self.assertIn("passed (current) [manual]", self.check("status"))

    def test_nonzero_status_stops_shell_batch_and_check_runs_once(self):
        result = subprocess.run(
            ["sh", "-ec", '"$1" task check -- sh -c "echo attempt; exit 23"; touch continued',
             "sh", TOOL], cwd=self.repo, env=self.env, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertFalse((self.repo / "continued").exists())
        record, = check_records(self.context)
        self.assertEqual((self.task / record["evidence"]).read_text(), "attempt\n")
        self.assertEqual(record["exit_code"], 23)

    def test_shared_lock_excludes_other_sessions_and_releases_after_interruption(self):
        first = subprocess.Popen(
            [TOOL, "task", "check", "--session", self.implementation, "--heavy", "--",
             "sh", "-c", "touch first-started; exec sleep 60"],
            cwd=self.repo, env=self.env, stderr=subprocess.PIPE, text=True,
        )
        with first:
            try:
                deadline = time.monotonic() + 5
                while not (self.repo / "first-started").exists():
                    self.assertIsNone(first.poll())
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.01)
                second = subprocess.Popen(
                    [TOOL, "task", "check", "--session", self.reviewer, "--heavy", "--",
                     "sh", "-c", "touch second-started"],
                    cwd=self.repo, env=self.env, stderr=subprocess.PIPE, text=True,
                )
                with second:
                    try:
                        self.assertIn("Check output", second.stderr.readline())
                        with self.assertRaises(subprocess.TimeoutExpired):
                            second.wait(timeout=0.35)
                        self.assertFalse((self.repo / "second-started").exists())
                        first.terminate()
                        self.assertEqual(first.wait(timeout=5), -signal.SIGTERM)
                        self.assertEqual(second.wait(timeout=5), 0)
                    finally:
                        if second.poll() is None:
                            second.terminate()
            finally:
                if first.poll() is None:
                    first.terminate()
        self.assertTrue((self.repo / "second-started").exists())
        interrupted, passed = check_records(self.context)
        self.assertEqual(interrupted["termination_signal"], signal.SIGTERM)
        self.assertGreater(passed["lock_wait_seconds"], 0)

    def test_child_signal_is_preserved_and_private_temp_directory_is_removed(self):
        tmp_parent = self.task / "temporary"
        tmp_parent.mkdir()
        self.check("--tmp-dir", tmp_parent, "--", "sh", "-c",
                   'printf "%s" "$TMPDIR"; kill -TERM $$', expected=-signal.SIGTERM)
        record, = check_records(self.context)
        temp = Path((self.task / record["evidence"]).read_text())
        self.assertEqual(temp.parent, tmp_parent)
        self.assertFalse(temp.exists())
        self.assertIsNone(record["exit_code"])
        self.assertEqual(record["termination_signal"], signal.SIGTERM)

    def test_source_freshness_distinguishes_unavailable_changed_and_historical(self):
        earlier = {"revision": "old", "content_sha256": "hash"}
        later = {"revision": "new", "content_sha256": "hash"}
        record = {"source_before": earlier, "source_after": earlier}
        self.assertEqual(freshness(record, earlier), "current")
        self.assertEqual(freshness(record, later), "historical")
        self.assertEqual(freshness(record, {}), "source unavailable")
        record["source_after"] = later
        self.assertEqual(freshness(record, later), "source changed during check")
