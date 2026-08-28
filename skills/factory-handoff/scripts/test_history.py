#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).parent
VALIDATOR = SCRIPTS / "validate-history.py"
REBUILDER = SCRIPTS / "rebuild-timeline.py"


class HistoryTests(unittest.TestCase):
    def write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def make_history(self, root: Path, verification_verdict: str = "pass") -> None:
        self.write(root / "history/checkpoints/000001-review/manifest.md", """---
checkpoint_sequence: 1
lifecycle: REVIEW
created_at: 2026-08-28T10:00:00Z
actor_outcome: succeeded
review_verdict: reject
selection_rationale: Review found a defect.
---
""")
        self.write(root / "history/checkpoints/000002-verification/manifest.md", f"""---
checkpoint_sequence: 2
lifecycle: VERIFICATION
created_at: 2026-08-28T12:00:00Z
actor_outcome: succeeded
verification_verdict: {verification_verdict}
selection_rationale: Verification checked the final revision.
---
""")
        self.write(root / "history/routes/000001-review--implementation/decision.md", """---
route_sequence: 1
from: REVIEW
created_at: 2026-08-28T10:01:00Z
selected:
  to: IMPLEMENTATION
  edge: implementation defect
  rationale: Review found a defect.
---
""")
        self.write(root / "history/routes/000001-review--implementation/disposition.md", """---
route_sequence: 1
status: committed
decided_at: 2026-08-28T10:02:00Z
transition_committed: true
committed_lifecycle: IMPLEMENTATION
approval_reference: automatic route
---
""")

    def test_rebuilds_counts_from_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_history(root)
            subprocess.run(["python3", str(REBUILDER), str(root)], check=True)
            timeline = (root / "history/timeline.md").read_text(encoding="utf-8")
            self.assertIn("checkpoints 2 | routes 1 | rework loops 1 | rejected routes 0", timeline)
            result = subprocess.run(["python3", str(VALIDATOR), str(root)], text=True, capture_output=True, check=False)
            self.assertEqual(0, result.returncode, result.stderr)

    def test_rejects_qualified_verification_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_history(root, "pass with items to settle")
            result = subprocess.run(
                ["python3", str(VALIDATOR), str(root), "--skip-timeline"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(1, result.returncode)
            self.assertIn("invalid verification_verdict", result.stderr)


if __name__ == "__main__":
    unittest.main()
