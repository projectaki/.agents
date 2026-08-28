#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


VALIDATOR = Path(__file__).with_name("validate-state.py")


VALID_STATE = """---
schema_version: 1
project_slug: example
branch_slug: feature--example
objective: Add the requested behavior.
task_revision: 1
status: lifecycle_active
current_lifecycle: IMPLEMENTATION
last_checkpointed_lifecycle: PLANNING
latest_handoff: planning/handoff.md
change_assurance_report: null
proof_ledger: proof-ledger.yaml
git_head: null
git_branch: feature/example
worktree_dirty: false
pending_transition: null
active_assignment: implementation-r1
active_attempt: 1
attempted_model_tiers: [standard]
stale_artifacts: []
checkpoint_sequence: 4
latest_snapshot: history/checkpoints/000004-planning/manifest.md
route_sequence: 4
latest_route_record: history/routes/000004-planning--implementation/decision.md
updated_at: 2026-08-28T10:00:00Z
---
"""


class ValidateStateTests(unittest.TestCase):
    def run_validator(self, content: str, *arguments: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.md"
            path.write_text(content, encoding="utf-8")
            return subprocess.run(["python3", str(VALIDATOR), str(path), *arguments], text=True, capture_output=True, check=False)

    def test_accepts_structured_current_state(self) -> None:
        result = self.run_validator(VALID_STATE)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_rejects_narrative_after_front_matter(self) -> None:
        result = self.run_validator(VALID_STATE + "Historical narrative.\n")
        self.assertEqual(1, result.returncode)
        self.assertIn("front matter only", result.stderr)

    def test_legacy_state_requires_migration(self) -> None:
        legacy = "---\nproject_slug: example\ncurrent_lifecycle: PLANNING\n---\nLegacy narrative.\n"
        self.assertEqual(1, self.run_validator(legacy).returncode)
        self.assertEqual(0, self.run_validator(legacy, "--allow-legacy").returncode)


if __name__ == "__main__":
    unittest.main()
