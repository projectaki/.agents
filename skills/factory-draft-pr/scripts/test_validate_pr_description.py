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

Concurrent renewal retains the requested destination.

- **Affected surface:** Component
- **Evidence:** Automated — [SessionRenewalTests](https://github.com/example/app/blob/0123456789abcdef0123456789abcdef01234567/tests/SessionRenewalTests.cs#L10) passed at the reviewed commit
- **Verdict:** Pass
- **Residual risk or waiver:** None

---

Cross-region failover keeps the renewed session valid.

- **Affected surface:** System
- **Evidence:** Inspection — [SessionStore.cs](https://github.com/example/app/blob/0123456789abcdef0123456789abcdef01234567/src/SessionStore.cs#L20) preserves the shared token contract
- **Verdict:** Waiver accepted
- **Residual risk or waiver:** Cross-region failover remains unproven. I accepted this gap because no test environment has two regions.

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
        body = VALID_BODY.replace("- **Residual risk or waiver:** None\n", "")
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("exactly 4 labeled fields" in error for error in errors))

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

    def test_requires_a_commit_pinned_file_permalink(self) -> None:
        body = VALID_BODY.replace(
            "[SessionRenewalTests](https://github.com/example/app/blob/0123456789abcdef0123456789abcdef01234567/tests/SessionRenewalTests.cs#L10) passed at the reviewed commit",
            "The test passed locally",
        )
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("requires at least 1 commit-pinned" in error for error in errors))

    def test_rejects_branch_file_link(self) -> None:
        body = VALID_BODY.replace(
            "/blob/0123456789abcdef0123456789abcdef01234567/",
            "/blob/main/",
        )
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("is not a commit-pinned" in error for error in errors))

    def test_rejects_regression_table(self) -> None:
        regression_section = """\
## Regression assurance

| Behavior at risk | Affected surface | Evidence | Verdict | Residual risk or waiver |
|---|---|---|---|---|
| Renewal works | Component | Automated — evidence | Pass | None |
"""
        start = VALID_BODY.index("## Regression assurance")
        end = VALID_BODY.index("## Manual test steps")
        body = VALID_BODY[:start] + regression_section + "\n" + VALID_BODY[end:]
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("stacked entries, not a table" in error for error in errors))

    def test_requires_blank_lines_around_entry_separator(self) -> None:
        body = VALID_BODY.replace("\n\n---\n\n", "\n---\n")
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("entry separators" in error for error in errors))

    def test_rejects_rule_after_last_entry(self) -> None:
        body = VALID_BODY.replace(
            "\n## Manual test steps",
            "\n---\n\n## Manual test steps",
        )
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("must not have a rule after the last entry" in error for error in errors))

    def test_rejects_entry_heading(self) -> None:
        body = VALID_BODY.replace(
            "Concurrent renewal retains the requested destination.",
            "### Concurrent renewal\n\nConcurrent renewal retains the requested destination.",
        )
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("must not have a heading" in error for error in errors))

    def test_rejects_unknown_affected_surface(self) -> None:
        body = VALID_BODY.replace("- **Affected surface:** Component", "- **Affected surface:** API", 1)
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("Data, Component, or System" in error for error in errors))

    def test_rejects_manual_evidence(self) -> None:
        body = VALID_BODY.replace("- **Evidence:** Automated —", "- **Evidence:** Manual —", 1)
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("Automated —" in error for error in errors))

    def test_requires_exact_verdict(self) -> None:
        body = VALID_BODY.replace("- **Verdict:** Pass", "- **Verdict:** PASS", 1)
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("verdict must be exactly" in error for error in errors))

    def test_waiver_requires_an_acceptor(self) -> None:
        body = VALID_BODY.replace(
            "I accepted this gap because no test environment has two regions.",
            "No test environment has two regions.",
        )
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("must say who accepted it" in error for error in errors))

    def test_waiver_requires_an_unproven_gap(self) -> None:
        body = VALID_BODY.replace(
            "Cross-region failover remains unproven. I accepted this gap because no test environment has two regions.",
            "I accepted this gap because its impact is low.",
        )
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("must name what is unproven" in error for error in errors))

    def test_waiver_requires_an_acceptance_reason(self) -> None:
        body = VALID_BODY.replace(
            "I accepted this gap because no test environment has two regions.",
            "I accepted this unproven gap.",
        )
        errors = VALIDATOR.validate(body)
        self.assertTrue(any("must say why it was accepted" in error for error in errors))

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
