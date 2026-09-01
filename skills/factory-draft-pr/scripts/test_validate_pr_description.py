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
## What changed

- Signed-in users now stay on the requested page when their session is renewed.
- Existing session data remains compatible without migration.

## Blast radius

- The widest code path is session renewal through signed-in navigation.
- A failure sends a signed-in user to the default page instead of the requested page.
- Rollback does not rewrite data or require a database migration. Redeploying the previous build is sufficient.

## Regression assurance

| Behavior at risk | Affected surface | Evidence | Verdict | Residual risk or waiver |
|---|---|---|---|---|
| Concurrent renewal retains destination | Signed-in navigation | Automated — [test and command](https://example.test/code) passed locally at the supplied commit | Pass | None |

## Manual test steps

### Developer checks

1. Renew a session and confirm that the requested page opens.

### Reviewer checks

1. Renew a session and confirm that the requested page opens.
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
        body = VALID_BODY.replace(
            "## Manual test steps",
            "## Validation\n\nPassed.\n\n## Manual test steps",
        )
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("level-2 sections" in error for error in errors))

    def test_rejects_template_comments(self) -> None:
        body = VALID_BODY.replace(
            "- Existing session data remains compatible without migration.",
            "<!-- Add compatibility details. -->\n"
            "- Existing session data remains compatible without migration.",
        )
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("template comments" in error for error in errors))

    def test_accepts_body_without_manual_test_steps(self) -> None:
        body = VALID_BODY.split("\n## Manual test steps", maxsplit=1)[0] + "\n"
        self.assertEqual([], VALIDATOR.validate(body))

    def test_rejects_missing_blast_radius(self) -> None:
        blast_radius = """\
## Blast radius

- The widest code path is session renewal through signed-in navigation.
- A failure sends a signed-in user to the default page instead of the requested page.
- Rollback does not rewrite data or require a database migration. Redeploying the previous build is sufficient.

"""
        errors = VALIDATOR.validate(VALID_BODY.replace(blast_radius, ""))
        self.assertTrue(any("level-2 sections" in error for error in errors))

    def test_rejects_manual_test_steps_before_regression_assurance(self) -> None:
        regression_start = VALID_BODY.index("## Regression assurance")
        manual_start = VALID_BODY.index("## Manual test steps")
        regression_section = VALID_BODY[regression_start:manual_start]
        manual_section = VALID_BODY[manual_start:]
        body = (
            VALID_BODY[:regression_start]
            + manual_section.rstrip()
            + "\n\n"
            + regression_section
        )
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("level-2 sections" in error for error in errors))

    def test_requires_a_durable_link_for_automated_evidence(self) -> None:
        body = VALID_BODY.replace(
            "[test and command](https://example.test/code) passed locally at the supplied commit",
            "The test passed locally",
        )
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("requires at least 1 durable link" in error for error in errors))

    def test_rejects_third_person_reference_to_author(self) -> None:
        body = VALID_BODY.replace(
            "- Signed-in users now stay on the requested page when their session is renewed.",
            "- Signed-in users now stay on the requested page when their session is renewed. "
            "Tell the author if you disagree.",
        )
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("third-person author voice" in error for error in errors))

    def test_rejects_invented_team_request(self) -> None:
        body = VALID_BODY.replace(
            "- The widest code path is session renewal through signed-in navigation.",
            "- Four checks the team asks a reviewer to make.",
        )
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("third-person author voice" in error for error in errors))

    def test_accepts_first_person_developer_position(self) -> None:
        body = VALID_BODY.replace(
            "- The widest code path is session renewal through signed-in navigation.",
            "- I kept renewal atomic because partial renewal could discard the destination.",
        )
        self.assertEqual([], VALIDATOR.validate(body))

    def test_normalizes_line_endings_and_trailing_newline(self) -> None:
        self.assertEqual(
            VALIDATOR.normalize(VALID_BODY),
            VALIDATOR.normalize(VALID_BODY.replace("\n", "\r\n").rstrip()),
        )


if __name__ == "__main__":
    unittest.main()
