"""Session records: allocation, events, turns, last-turn.md, bind, and status."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from x_env import records
from x_env.model import (
    Access,
    HarnessName,
    Project,
    SessionName,
    TaskName,
    XEnvError,
)
from x_env.records import (
    Exited,
    Finished,
    HarnessBinding,
    LaunchFacts,
    Lost,
    Prepared,
    Running,
    Started,
    TurnEnded,
    TurnStarted,
)

T0 = datetime(2026, 11, 18, 10, 2, 11, tzinfo=timezone.utc)
HOST = "laptop"


def at(seconds):
    return T0 + timedelta(seconds=seconds)


def facts(host=HOST, binding=None):
    return LaunchFacts(
        harness=HarnessName.CODEX, model="gpt-5", effort="high", access=Access.AUTO,
        mode="headless", host=host, cwd=Path("/w/p/tasks/fix/repo"), prompt="Review the diff",
        binding=binding,
    )


def started(pid=None, process_start=None):
    pid = os.getpid() if pid is None else pid
    if process_start is None:
        process_start = records.process_start_time(pid)
    return Started(at=at(0), pid=pid, process_start=process_start, terminal="none", terminal_handle=None)


class RecordsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Project(Path(temporary.name) / "shop")
        self.task = self.project.task(TaskName("fix"))

    def create(self, name="review", host=HOST, binding=None):
        return records.create(self.task, SessionName(name), facts(host, binding), T0)

    # --- create, find, list ---------------------------------------------------

    def test_numbers_increase_across_names_and_survive_the_task_folder(self):
        first = self.create("chief")
        second = self.create("review")
        third = self.create("chief")
        self.assertEqual([first.id, second.id, third.id], ["fix/001-chief", "fix/002-review", "fix/003-chief"])
        self.assertEqual(first.path, self.project.path / "sessions/fix/001-chief")

    def test_a_folder_left_by_a_crash_keeps_its_number_and_is_not_listed(self):
        self.create("chief")
        (self.task.records / "002-crashed").mkdir()
        self.assertEqual(self.create("review").id, "fix/003-review")
        listed = [r.id for r in records.list_sessions(self.project.sessions_dir)]
        self.assertEqual(listed, ["fix/001-chief", "fix/003-review"])

    def test_session_json_holds_the_launch_facts(self):
        record = self.create()
        data = json.loads((record.path / "session.json").read_text())
        self.assertEqual(data["schema"], 1)
        self.assertEqual(data["id"], "fix/001-review")
        self.assertEqual((data["project"], data["task"], data["name"]), ("shop", "fix", "review"))
        self.assertEqual(data["created_at"], "2026-11-18T10:02:11.000Z")
        self.assertEqual(data["launch"], {
            "harness": "codex", "model": "gpt-5", "effort": "high", "access": "auto",
            "mode": "headless", "host": HOST, "cwd": "/w/p/tasks/fix/repo",
            "prompt": "Review the diff", "binding": None,
        })
        self.assertEqual(record.meta().launch, facts())

    def test_unknown_schema_is_rejected_with_the_file_name(self):
        record = self.create()
        data = json.loads(record.meta_path.read_text())
        record.meta_path.write_text(json.dumps({**data, "schema": 99}))
        with self.assertRaisesRegex(XEnvError, "session.json"):
            record.meta()

    def test_find_accepts_full_id_number_and_absolute_path(self):
        self.create("chief")
        review = self.create("review")
        root = self.project.sessions_dir
        for ref in ("fix/002-review", "fix/002", "fix/2", str(review.path)):
            with self.subTest(ref=ref):
                self.assertEqual(records.find(root, ref), review)
        for ref in ("fix/003", "fix/002-other", "other/001-chief"):
            with self.subTest(ref=ref):
                with self.assertRaisesRegex(XEnvError, "Session not found"):
                    records.find(root, ref)

    # --- events -------------------------------------------------------------

    def test_events_are_appended_in_order(self):
        record = self.create()
        record.append(started())
        record.append(TurnStarted(at(1)))
        record.append(Exited(at(5), exit_code=3))
        lines = [json.loads(line) for line in record.events_path.read_text().splitlines()]
        self.assertEqual([line["event"] for line in lines], ["started", "turn_started", "exited"])
        self.assertEqual(lines[2], {"event": "exited", "at": "2026-11-18T10:02:16.000Z", "exit_code": 3})
        self.assertEqual(list(record.events()), [started(), TurnStarted(at(1)), Exited(at(5), 3)])

    def test_a_torn_last_line_is_skipped_and_not_merged_into_the_next_event(self):
        record = self.create()
        record.append(started())
        with record.events_path.open("a") as stream:
            stream.write('{"event": "turn_sta')
        self.assertEqual(list(record.events()), [started()])
        record.append(TurnStarted(at(2)))
        self.assertEqual(list(record.events()), [started(), TurnStarted(at(2))])

    # --- turns ----------------------------------------------------------------

    def test_turn_numbers_and_durations_come_from_earlier_events(self):
        record = self.create()
        record.append(started())
        record.append(TurnStarted(at(10)))
        first = record.append_turn_end(at(25.5))
        record.append(TurnStarted(at(100)))
        second = record.append_turn_end(at(160))
        self.assertEqual(first, TurnEnded(at(25.5), turn=1, duration_s=15.5))
        self.assertEqual(second, TurnEnded(at(160), turn=2, duration_s=60.0))
        self.assertEqual([e for e in record.events() if isinstance(e, TurnEnded)], [first, second])

    def test_turn_without_turn_started_is_measured_from_started(self):
        record = self.create()
        record.append(started())
        self.assertEqual(record.append_turn_end(at(7)).duration_s, 7.0)

    def test_turn_without_its_own_turn_started_is_measured_from_the_previous_end(self):
        record = self.create()
        record.append(started())
        record.append(TurnStarted(at(10)))
        first = record.append_turn_end(at(20))
        second = record.append_turn_end(at(50))
        self.assertEqual(first.duration_s, 10.0)
        self.assertEqual(second, TurnEnded(at(50), turn=2, duration_s=30.0))

    def test_each_turn_with_a_turn_started_is_measured_from_its_own_start(self):
        record = self.create()
        record.append(started())
        record.append(TurnStarted(at(10)))
        record.append_turn_end(at(20))
        record.append(TurnStarted(at(100)))
        second = record.append_turn_end(at(130))
        record.append(TurnStarted(at(200)))
        third = record.append_turn_end(at(201))
        self.assertEqual([second.duration_s, third.duration_s], [30.0, 1.0])

    def test_last_turn_is_replaced_each_turn(self):
        record = self.create()
        record.set_last_turn("First answer\n")
        record.set_last_turn("Second answer\n")
        self.assertEqual(record.last_turn_path.read_text(), "Second answer\n")
        self.assertEqual(sorted(p.name for p in record.path.iterdir()), ["last-turn.md", "session.json"])

    # --- bind -------------------------------------------------------------------

    def test_bind_fills_the_binding_once(self):
        record = self.create()
        binding = HarnessBinding("abc", Path("/home/u/.codex/sessions/rollout-abc.jsonl"))
        record.bind(binding)
        record.bind(binding)
        self.assertEqual(record.meta().launch.binding, binding)
        self.assertEqual(record.meta().launch.model, "gpt-5")
        with self.assertRaisesRegex(XEnvError, "already bound"):
            record.bind(HarnessBinding("other", Path("/other.jsonl")))
        self.assertEqual(record.meta().launch.binding, binding)

    # --- status -----------------------------------------------------------------

    def test_status_folds_the_events(self):
        record = self.create()
        self.assertEqual(record.status(HOST), Prepared())
        record.append(started())
        record.append(TurnStarted(at(1)))
        record.append_turn_end(at(2))
        self.assertEqual(record.status(HOST), Running(started(), turns=1))
        record.append(Exited(at(3), exit_code=0))
        self.assertEqual(record.status(HOST), Finished(Exited(at(3), 0), turns=1))

    def test_a_started_session_whose_process_is_gone_is_lost(self):
        child = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"],
                               capture_output=True, text=True, check=True)
        gone = started(pid=int(child.stdout), process_start="1")
        record = self.create()
        record.append(gone)
        self.assertEqual(record.status(HOST), Lost(gone, turns=0))

    def test_a_reused_pid_does_not_count_as_running(self):
        reused = started(process_start="0")
        record = self.create()
        record.append(reused)
        self.assertEqual(record.status(HOST), Lost(reused, turns=0))

    def test_a_session_on_another_host_is_not_checked_locally(self):
        remote = started(pid=999_999_999, process_start="1")
        record = self.create(host="vps")
        record.append(remote)
        self.assertEqual(record.status(HOST), Running(remote, turns=0))


if __name__ == "__main__":
    unittest.main()
