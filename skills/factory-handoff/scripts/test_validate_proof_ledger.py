#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


VALIDATOR = Path(__file__).with_name("validate-proof-ledger.py")


class ProofLedgerValidatorTests(unittest.TestCase):
    def validate(self, content: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proof-ledger.yaml"
            path.write_text(content, encoding="utf-8")
            return subprocess.run(["python3", str(VALIDATOR), str(path)], text=True, capture_output=True, check=False)

    def test_accepts_closed_universal_claim(self) -> None:
        result = self.validate("""schema_version: 1
task_revision: 1
updated_at: 2026-08-28T10:00:00Z
claims:
  - claim_id: AC-001
    statement: Every upload endpoint rejects an unknown organization.
    source: intake/handoff.md
    status: active
    path_ids: [PATH-001]
    risk_ids: [RISK-001]
    inventory:
      status: closed
      items:
        - item_id: questionnaire-upload
          name: Questionnaire upload
          source: src/Controller.cs
    proof_obligations:
      - proof_id: PROOF-001
        requirement: Reject the request before storage access.
        required_method: automated
        planned_method: automated
        evidence: []
        verdict: unverified
        exception: null
""")
        self.assertEqual(0, result.returncode, result.stderr)

    def test_rejects_proof_substitution_without_exception(self) -> None:
        result = self.validate("""schema_version: 1
task_revision: 1
updated_at: 2026-08-28T10:00:00Z
claims:
  - claim_id: AC-001
    statement: The upload endpoint rejects an unknown organization.
    source: intake/handoff.md
    status: active
    path_ids: [PATH-001]
    risk_ids: []
    inventory: null
    proof_obligations:
      - proof_id: PROOF-001
        requirement: Reject the request before storage access.
        required_method: automated
        planned_method: inspection
        evidence: []
        verdict: unverified
        exception: null
""")
        self.assertEqual(1, result.returncode)
        self.assertIn("without an accepted exception", result.stderr)

    def test_rejects_open_universal_inventory(self) -> None:
        result = self.validate("""schema_version: 1
task_revision: 1
updated_at: 2026-08-28T10:00:00Z
claims:
  - claim_id: AC-001
    statement: Every upload endpoint rejects an unknown organization.
    source: intake/handoff.md
    status: active
    path_ids: []
    risk_ids: []
    inventory:
      status: open
      items: []
    proof_obligations:
      - proof_id: PROOF-001
        requirement: Reject the request.
        required_method: automated
        planned_method: automated
        evidence: []
        verdict: unverified
        exception: null
""")
        self.assertEqual(1, result.returncode)
        self.assertIn("inventory must be closed", result.stderr)

    def test_rejects_exception_for_another_claim_or_path(self) -> None:
        result = self.validate("""schema_version: 1
task_revision: 1
updated_at: 2026-08-28T10:00:00Z
claims:
  - claim_id: AC-001
    statement: The upload endpoint rejects an unknown organization.
    source: intake/handoff.md
    status: active
    path_ids: [PATH-001]
    risk_ids: []
    inventory: null
    proof_obligations:
      - proof_id: PROOF-001
        requirement: Reject the request before storage access.
        required_method: automated
        planned_method: inspection
        evidence: []
        verdict: waived
        exception:
          status: accepted
          claim_ids: [AC-002]
          path_ids: [PATH-002]
          approval_reference: planning/handoff.md
          residual_risk: No direct integration test exists.
""")
        self.assertEqual(1, result.returncode)
        self.assertIn("must include its current claim", result.stderr)
        self.assertIn("paths outside its claim", result.stderr)


if __name__ == "__main__":
    unittest.main()
