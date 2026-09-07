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
    def test_accepts_complete_body(self) -> None:
        self.assertEqual([], VALIDATOR.validate(VALID_BODY))

    def test_accepts_legitimate_product_names(self) -> None:
        body = VALID_BODY.replace("Concurrent renewal", "R2 storage bucket renewal")
        self.assertEqual([], VALIDATOR.validate(body))

    def test_accepts_equivalent_presentations(self) -> None:
        variants = [
            VALID_BODY.replace("Concurrent renewal retains", "### Concurrent renewal retains"),
            VALID_BODY.replace("Component", "Session renewal API"),
            VALID_BODY.replace("Automated — ", "Test result: "),
            VALID_BODY.replace("**Verdict:** Pass", "**Verdict:** PASS"),
            VALID_BODY.replace("\n\n---\n\n", "\n---\n"),
            VALID_BODY.replace("\n## Manual test steps", "\n---\n\n## Manual test steps"),
            VALID_BODY.replace("## Manual test steps", "## Compatibility\n\nExisting sessions remain valid.\n\n## Manual test steps"),
            VALID_BODY.replace("- **Verdict:** Pass\n- **Residual risk or waiver:** None", "- **Residual risk or waiver:** None\n\n- **Verdict:** Pass"),
        ]
        for body in variants:
            with self.subTest(body=body):
                self.assertEqual([], VALIDATOR.validate(body))

    def test_accepts_sections_in_another_order(self) -> None:
        start = VALID_BODY.index("## Regression assurance")
        end = VALID_BODY.index("## Manual test steps")
        body = VALID_BODY[:start] + VALID_BODY[end:] + "\n" + VALID_BODY[start:end]
        self.assertEqual([], VALIDATOR.validate(body))

    def test_accepts_body_without_manual_steps(self) -> None:
        self.assertEqual([], VALIDATOR.validate(VALID_BODY.split("\n## Manual test steps")[0]))

    def test_accepts_approval_wording_without_prescribed_grammar(self) -> None:
        body = VALID_BODY.replace(
            "I accepted this gap because no test environment has two regions.",
            "My approval covers this gap: a two-region test environment is unavailable.",
        )
        self.assertEqual([], VALIDATOR.validate(body))

    def test_rejects_missing_required_sections(self) -> None:
        for name in VALIDATOR.REQUIRED_SECTIONS:
            with self.subTest(name=name):
                body = VALID_BODY.replace(f"## {name}", f"## Other {name}")
                self.assertTrue(VALIDATOR.validate(body))

    def test_rejects_empty_required_section(self) -> None:
        body = VALID_BODY.replace("## Blast radius", "## Blast radius\n\n## Other details")
        self.assertTrue(VALIDATOR.validate(body))

    def test_rejects_duplicate_section(self) -> None:
        self.assertTrue(VALIDATOR.validate(VALID_BODY + "\n## What changed\n\nOther behavior.\n"))

    def test_rejects_template_comments(self) -> None:
        self.assertTrue(VALIDATOR.validate(VALID_BODY + "\n<!-- Explain the change. -->"))

    def test_requires_each_evidence_field(self) -> None:
        for label in VALIDATOR.REQUIRED_FIELDS:
            with self.subTest(label=label):
                body = "\n".join(line for line in VALID_BODY.splitlines() if not line.startswith(f"- **{label}:**"))
                self.assertTrue(VALIDATOR.validate(body))

    def test_requires_behavior_for_each_entry(self) -> None:
        body = VALID_BODY.replace("Concurrent renewal retains the requested destination.\n", "")
        self.assertTrue(VALIDATOR.validate(body))

    def test_rejects_duplicate_field(self) -> None:
        body = VALID_BODY.replace("- **Verdict:** Pass", "- **Verdict:** Pass\n- **Verdict:** Fail")
        self.assertTrue(VALIDATOR.validate(body))

    def test_requires_commit_pinned_evidence_for_each_entry(self) -> None:
        body = VALID_BODY.replace(
            "[SessionRenewalTests](https://github.com/example/app/blob/0123456789abcdef0123456789abcdef01234567/tests/SessionRenewalTests.cs#L10)",
            "The test passed locally",
        )
        self.assertTrue(VALIDATOR.validate(body))

    def test_rejects_branch_evidence_link(self) -> None:
        body = VALID_BODY.replace("/blob/0123456789abcdef0123456789abcdef01234567/", "/blob/main/")
        self.assertTrue(VALIDATOR.validate(body))

    def test_rejects_unresolved_verdict(self) -> None:
        body = VALID_BODY.replace("**Verdict:** Pass", "**Verdict:** Pending")
        self.assertTrue(VALIDATOR.validate(body))

    def test_waiver_cannot_claim_no_gap(self) -> None:
        body = VALID_BODY.replace("**Verdict:** Pass", "**Verdict:** Waiver accepted", 1)
        self.assertTrue(VALIDATOR.validate(body))

    def test_normalizes_line_endings(self) -> None:
        self.assertEqual(VALIDATOR.normalize(VALID_BODY), VALIDATOR.normalize(VALID_BODY.replace("\n", "\r\n").rstrip()))

    def test_publication_readback_must_match(self) -> None:
        import subprocess
        import sys
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            expected = Path(directory) / "expected.md"
            published = Path(directory) / "published.md"
            expected.write_text(VALID_BODY)
            published.write_text(VALID_BODY)
            command = [sys.executable, str(SCRIPT), str(published), "--expected", str(expected)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            published.write_text(VALID_BODY.replace("Concurrent renewal", "Sequential renewal"))
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(1, result.returncode)
            self.assertIn("does not exactly match", result.stderr)


if __name__ == "__main__":
    unittest.main()
