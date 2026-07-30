#!/usr/bin/env python3
"""Tests for Factory lifecycle path resolution."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("resolve-handoff-path.sh")
LIFECYCLES = (
    "INTAKE",
    "CONTEXT_GATHERING",
    "REPLICATION",
    "ANALYSIS",
    "PLANNING",
    "IMPLEMENTATION",
    "REVIEW",
    "VIDEO_EVIDENCE",
    "VERIFICATION",
    "DELIVERY",
    "AWAITING_INPUT",
    "COMPLETED",
    "CANCELLED",
)


class ResolveHandoffPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        subprocess.run(["git", "init", "-q", "-b", "feature/example", self.root], check=True)
        self.environment = {**os.environ, "HOME": str(self.root / "home")}

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def resolve(self, lifecycle: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [SCRIPT, lifecycle],
            cwd=self.root,
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_resolves_current_lifecycles(self) -> None:
        for lifecycle in LIFECYCLES:
            with self.subTest(lifecycle=lifecycle):
                result = self.resolve(lifecycle)
                self.assertEqual(0, result.returncode, result.stderr)

    def test_rejects_folded_lifecycles(self) -> None:
        for lifecycle in ("TEST_SCOPE", "REGRESSION_SCOPE"):
            with self.subTest(lifecycle=lifecycle):
                result = self.resolve(lifecycle)
                self.assertEqual(2, result.returncode)
                self.assertIn("unknown orchestrator lifecycle", result.stderr)


if __name__ == "__main__":
    unittest.main()
