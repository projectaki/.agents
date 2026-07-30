#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

VALIDATOR = Path(__file__).with_name("validate-human-report.py")


class ValidateHumanReportTest(unittest.TestCase):
    def run_validator(self, content: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temp_directory:
            report_path = Path(temp_directory) / "report.md"
            report_path.write_text(content, encoding="utf-8")
            return subprocess.run(
                ["python3", str(VALIDATOR), str(report_path)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_accepts_plain_readable_report(self) -> None:
        result = self.run_validator(
            """# Ready for planning

The account endpoint will validate expired sessions before loading profile data.

| Behavior | Result | Evidence |
| --- | --- | --- |
| Expired session | Rejected | Integration test |
"""
        )

        self.assertEqual(0, result.returncode, result.stderr)

    def test_rejects_internal_ids_jargon_and_wide_tables(self) -> None:
        result = self.run_validator(
            """# P4

This is a faithful port.

| A | B | C | D | E |
| --- | --- | --- | --- | --- |
| 1 | 2 | 3 | 4 | 5 |
"""
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("internal ID", result.stderr)
        self.assertIn("prohibited jargon", result.stderr)
        self.assertIn("5 columns", result.stderr)

    def test_rejects_count_based_mermaid_node(self) -> None:
        result = self.run_validator(
            """# System impact

```mermaid
flowchart LR
    Client --> API["4 endpoints"]
```
"""
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("count-based diagram node", result.stderr)


if __name__ == "__main__":
    unittest.main()
