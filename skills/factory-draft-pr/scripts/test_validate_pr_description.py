#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate-pr-description.py")
SPEC = importlib.util.spec_from_file_location("validate_pr_description", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


VALID_BODY = """\
## Task

Keep signed-in users on the requested page when their session is renewed.

## What changed

- Session renewal now retains the pending destination.

## Concerns raised during analysis

- Renewal could discard the destination when requests overlap.

## Regression assurance

| Behavior at risk | Affected surface | Evidence | Verdict | Residual risk or waiver |
|---|---|---|---|---|
| Concurrent renewal retains destination | Signed-in navigation | Automated — [test](https://example.test/code) · [result](https://example.test/run) | Pass | None |

## Gaps

None.
"""


class ValidatePrDescriptionTest(unittest.TestCase):
    def test_accepts_complete_plain_language_body(self) -> None:
        self.assertEqual([], VALIDATOR.validate(VALID_BODY))

    def test_rejects_internal_ids(self) -> None:
        errors = VALIDATOR.validate(VALID_BODY.replace("Concurrent renewal", "P14 renewal"))
        self.assertTrue(any("internal ID" in error for error in errors))

    def test_rejects_missing_regression_field(self) -> None:
        body = VALID_BODY.replace("| Pass | None |", "| Pass | |")
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("empty field" in error for error in errors))

    def test_rejects_extra_section(self) -> None:
        body = VALID_BODY.replace("## Gaps", "## Validation\n\nPassed.\n\n## Gaps")
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("level-2 sections" in error for error in errors))

    def test_rejects_template_comments(self) -> None:
        body = VALID_BODY.replace("None.", "<!-- Add gaps. -->\nNone.")
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("template comments" in error for error in errors))

    def test_requires_test_and_result_links_for_automated_evidence(self) -> None:
        body = VALID_BODY.replace(
            "[test](https://example.test/code) · [result](https://example.test/run)",
            "[test](https://example.test/code)",
        )
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("requires at least 2 durable link" in error for error in errors))

    def test_normalizes_line_endings_and_trailing_newline(self) -> None:
        self.assertEqual(
            VALIDATOR.normalize(VALID_BODY),
            VALIDATOR.normalize(VALID_BODY.replace("\n", "\r\n").rstrip()),
        )


if __name__ == "__main__":
    unittest.main()
