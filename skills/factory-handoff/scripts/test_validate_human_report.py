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

## At a glance

| | |
| --- | --- |
| Status | Ready for planning |
| Scope | Expired sessions |

## Expected behavior

The account endpoint will validate expired sessions before loading profile data.

| Behavior | Result | Evidence |
| --- | --- | --- |
| Expired session | Rejected | Integration test |

## Remaining risk

None identified.

## Next action

Approve the plan.
"""
        )

        self.assertEqual(0, result.returncode, result.stderr)

    def test_rejects_internal_ids_jargon_and_wide_tables(self) -> None:
        result = self.run_validator(
            """# P4

## At a glance

| Status | Ready |

This is a faithful port.

| A | B | C | D | E |
| --- | --- | --- | --- | --- |
| 1 | 2 | 3 | 4 | 5 |

## Remaining risk

None identified.

## Next action

Review the report.
"""
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("internal ID", result.stderr)
        self.assertIn("prohibited jargon", result.stderr)
        self.assertIn("5 columns", result.stderr)

    def test_rejects_count_based_mermaid_node(self) -> None:
        result = self.run_validator(
            """# System impact

## At a glance

| | |
| --- | --- |
| Status | Ready for analysis |

```mermaid
flowchart LR
    Client --> API["4 endpoints"]
```

## Remaining risk

None identified.

## Next action

Start analysis.
"""
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("count-based diagram node", result.stderr)

    def test_rejects_missing_human_orientation(self) -> None:
        result = self.run_validator(
            """# Implementation complete

All tests pass.
"""
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("At a glance", result.stderr)
        self.assertIn("Status row", result.stderr)
        self.assertIn("Remaining risk", result.stderr)
        self.assertIn("Next action", result.stderr)

    def test_rejects_dense_paragraph_and_long_list(self) -> None:
        paragraph = " ".join(["word"] * 101)
        items = "\n".join(f"- Item {number}" for number in range(1, 10))
        result = self.run_validator(
            f"""# Review: Changes required

## At a glance

| | |
| --- | --- |
| Status | Changes required |

## Findings

{paragraph}

{items}

## Remaining risk

The findings remain open.

## Next action

Correct the findings.
"""
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("paragraph has 101 words", result.stderr)
        self.assertIn("more than 8 consecutive items", result.stderr)

    def test_long_report_needs_a_second_visual_structure(self) -> None:
        sections = "\n\n".join(
            f"## Result {number}\n\n" + " ".join(["clear"] * 40)
            for number in range(1, 8)
        )
        result = self.run_validator(
            f"""# Analysis: Ready for planning

## At a glance

| | |
| --- | --- |
| Status | Ready for planning |

{sections}

## Remaining risk

None identified.

## Next action

Create the plan.
"""
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("in addition to the At a glance table", result.stderr)

    def test_rejects_report_over_word_budget(self) -> None:
        sections = "\n\n".join(
            f"## Result {number}\n\n" + " ".join(["clear"] * 90)
            for number in range(1, 7)
        )
        result = self.run_validator(
            f"""# Analysis: Ready for planning

## At a glance

| | |
| --- | --- |
| Status | Ready for planning |

## Impact map

| Area | Result |
| --- | --- |
| API | Affected |

{sections}

## Remaining risk

None identified.

## Next action

Create the plan.
"""
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("use at most 500", result.stderr)


if __name__ == "__main__":
    unittest.main()
