#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate-step-contracts.py")
SPEC = importlib.util.spec_from_file_location("validate_step_contracts", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


VALID_CONTRACT = """\
---
name: example
description: Example.
---

# Example

## Purpose

Do work.

## Inputs

Accept data.

## Operation

Process data.

## Outputs

Return a result.

## Side effects

Make no changes.

## Failure results

Return a blocker.

## Non-goals

Do not expand scope.
"""


class ValidateStepContractsTest(unittest.TestCase):
    def test_accepts_independent_contract(self) -> None:
        self.assertEqual([], VALIDATOR.validate_contract(VALID_CONTRACT))

    def test_rejects_handoff_file_dependency(self) -> None:
        text = VALID_CONTRACT.replace("Return a result.", "Write `report.md`.")
        errors = VALIDATOR.validate_contract(text)
        self.assertTrue(any("handoff file" in error for error in errors))

    def test_rejects_orchestration_branch(self) -> None:
        text = VALID_CONTRACT.replace("Do work.", "When orchestrated, do work.")
        errors = VALIDATOR.validate_contract(text)
        self.assertTrue(any("orchestration branch" in error for error in errors))

    def test_current_work_skills_are_valid(self) -> None:
        skills_root = SCRIPT.resolve().parents[2]
        errors = []
        for skill_name in VALIDATOR.WORK_SKILLS:
            errors.extend(VALIDATOR.validate_skill(skills_root / skill_name))
        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
