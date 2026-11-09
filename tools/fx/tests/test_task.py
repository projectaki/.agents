import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fx_task import task_layout


class TaskLayoutTest(unittest.TestCase):
    def test_layout_runs_the_startup_command_with_the_literal_task_path(self):
        task = Path('/tmp/task with "quotes", $dollars, `commands`, and æ\nnext')
        layout = task_layout(task, "claude")
        arguments = next(line.strip()[5:] for line in layout.splitlines() if line.strip().startswith("args "))
        decoder = json.JSONDecoder()
        values = []
        while arguments:
            value, offset = decoder.raw_decode(arguments)
            values.append(value)
            arguments = arguments[offset:].lstrip()
        self.assertEqual(values, [str(Path(__file__).resolve().parents[1] / "fx_task.py"), "shell", str(task), "claude"])
        self.assertIn('pane command="python3" close_on_exit=true', layout)
        self.assertIn('plugin location="tab-bar"', layout)
        self.assertIn('plugin location="status-bar"', layout)


if __name__ == "__main__":
    unittest.main()
