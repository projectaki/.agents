#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from records import LOW_RISK_CHECKS, validate_assurance, validate_root
from routing import decide


SCRIPTS = Path(__file__).parent
CHECKPOINT = SCRIPTS / "checkpoint.py"


def run_checkpoint(task_root: Path, lifecycle: str, outcome: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python3",
            str(CHECKPOINT),
            "--task-root",
            str(task_root),
            "--lifecycle",
            lifecycle,
            "--outcome",
            outcome,
            "--reason",
            f"{lifecycle} returned {outcome}.",
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def task(repository: Path, **values: object) -> dict[str, object]:
    document: dict[str, object] = {
        "schema_version": 1,
        "task_revision": 1,
        "status": "aligned",
        "repository": str(repository),
        "objective": "Add the requested behavior.",
        "acceptance_criteria": ["The behavior is observable."],
        "scope": {"included": ["Requested behavior"], "excluded": []},
        "authority": {
            "edit": True,
            "test": True,
            "commit": True,
            "push": False,
            "draft_pull_request": False,
        },
        "deliverable": "local_commit",
        "continuation_mode": "supervised",
        "open_decisions": [],
    }
    document.update(values)
    return document


def assurance(**values: object) -> dict[str, object]:
    document: dict[str, object] = {
        "schema_version": 1,
        "task_revision": 1,
        "risk_class": "low",
        "signals": {
            "impact": "low",
            "uncertainty": "low",
            "reasoning_difficulty": "low",
            "proof_difficulty": "low",
            "input_gaps": "low",
        },
        "low_risk_gate": {
            "eligible": True,
            "checks": {name: True for name in LOW_RISK_CHECKS},
        },
        "plan_assurance_required": False,
        "sensitive_change": False,
        "paths": [{"id": "path-1", "behavior": "Requested behavior"}],
        "risks": [],
        "diff_groups": [],
        "evidence": [],
        "exceptions": [],
        "blockers": [],
        "base_revision": None,
        "change_revision": "abc123",
        "verdict": "unverified",
        "routing": {
            "decision_required": False,
            "scope_changed": False,
            "risk_changed": False,
            "required_dependency_unavailable": False,
        },
    }
    document.update(values)
    return document


class RecordTests(unittest.TestCase):
    def test_low_risk_gate_fails_closed(self) -> None:
        document = assurance()
        document["low_risk_gate"]["checks"]["no_sensitive_change"] = False  # type: ignore[index]
        errors = validate_assurance(document, 1)
        self.assertIn("low-risk eligibility requires every check to pass", errors)

    def test_triage_routes_directly_to_implementation(self) -> None:
        decision = decide(task(Path("/tmp/repository")), assurance(), [], "TRIAGE", "ready")
        self.assertEqual("IMPLEMENTATION", decision.next_lifecycle)
        self.assertFalse(decision.stop)

    def test_plan_assurance_is_conditional(self) -> None:
        document = assurance(plan_assurance_required=True)
        decision = decide(task(Path("/tmp/repository")), document, [], "TRIAGE", "ready")
        self.assertEqual("PLAN_ASSURANCE", decision.next_lifecycle)

    def test_sensitive_change_requires_plan_assurance(self) -> None:
        document = assurance(sensitive_change=True)
        self.assertIn("a sensitive change requires plan assurance", validate_assurance(document, 1))

    def test_missing_commit_authority_stops_before_implementation(self) -> None:
        contract = task(Path("/tmp/repository"))
        contract["authority"]["commit"] = False  # type: ignore[index]
        decision = decide(contract, assurance(), [], "TRIAGE", "ready")
        self.assertEqual("AWAITING_INPUT", decision.next_lifecycle)
        self.assertTrue(decision.stop)

    def test_second_assurance_failure_stops(self) -> None:
        history = [{"lifecycle": "CHANGE_ASSURANCE", "next_lifecycle": "IMPLEMENTATION"}]
        document = assurance(verdict="fail")
        decision = decide(task(Path("/tmp/repository")), document, history, "CHANGE_ASSURANCE", "fail")
        self.assertEqual("AWAITING_INPUT", decision.next_lifecycle)
        self.assertTrue(decision.stop)

    def test_second_plan_rejection_stops(self) -> None:
        history = [{"lifecycle": "PLAN_ASSURANCE", "next_lifecycle": "TRIAGE"}]
        document = assurance(plan_assurance_required=True, verdict="plan_rejected")
        decision = decide(task(Path("/tmp/repository")), document, history, "PLAN_ASSURANCE", "reject")
        self.assertEqual("AWAITING_INPUT", decision.next_lifecycle)
        self.assertTrue(decision.stop)

    def test_implementation_requires_exact_clean_commit(self) -> None:
        document = assurance()
        dirty = decide(
            task(Path("/tmp/repository")),
            document,
            [],
            "IMPLEMENTATION",
            "complete",
            git_head="abc123",
            worktree_dirty=True,
        )
        wrong_head = decide(
            task(Path("/tmp/repository")),
            document,
            [],
            "IMPLEMENTATION",
            "complete",
            git_head="different",
            worktree_dirty=False,
        )
        clean = decide(
            task(Path("/tmp/repository")),
            document,
            [],
            "IMPLEMENTATION",
            "complete",
            git_head="abc123",
            worktree_dirty=False,
        )
        self.assertTrue(dirty.stop)
        self.assertTrue(wrong_head.stop)
        self.assertEqual("CHANGE_ASSURANCE", clean.next_lifecycle)

    def test_assured_local_change_completes_without_delivery(self) -> None:
        decision = decide(
            task(Path("/tmp/repository")),
            assurance(verdict="pass"),
            [],
            "CHANGE_ASSURANCE",
            "pass",
            git_head="abc123",
            worktree_dirty=False,
        )
        self.assertEqual("COMPLETED", decision.next_lifecycle)

    def test_draft_pull_request_requires_delivery_authority(self) -> None:
        contract = task(Path("/tmp/repository"), deliverable="draft_pull_request")
        decision = decide(
            contract,
            assurance(verdict="pass"),
            [],
            "CHANGE_ASSURANCE",
            "pass",
            git_head="abc123",
            worktree_dirty=False,
        )
        self.assertEqual("AWAITING_INPUT", decision.next_lifecycle)
        contract["authority"]["push"] = True  # type: ignore[index]
        contract["authority"]["draft_pull_request"] = True  # type: ignore[index]
        decision = decide(
            contract,
            assurance(verdict="pass"),
            [],
            "CHANGE_ASSURANCE",
            "pass",
            git_head="abc123",
            worktree_dirty=False,
        )
        self.assertEqual("DELIVERY", decision.next_lifecycle)

    def test_checkpoint_and_validate_compact_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository"
            task_root = root / "task"
            repository.mkdir()
            task_root.mkdir()
            subprocess.run(["git", "init", "-q", str(repository)], check=True)
            (task_root / "task.json").write_text(json.dumps(task(repository)), encoding="utf-8")
            (task_root / "assurance.json").write_text(json.dumps(assurance()), encoding="utf-8")
            report = "# Triage\n\nReady.\n"
            (task_root / "report.md").write_text(report, encoding="utf-8")

            result = run_checkpoint(task_root, "TRIAGE", "ready")
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual([], validate_root(task_root))
            route = json.loads(result.stdout)
            self.assertEqual("IMPLEMENTATION", route["next_lifecycle"])

            (task_root / "report.md").write_text("changed", encoding="utf-8")
            self.assertIn("report.md changed after the latest checkpoint", validate_root(task_root))
            (task_root / "report.md").write_text(report, encoding="utf-8")
            (repository / "untracked.txt").write_text("changed", encoding="utf-8")
            self.assertIn("Git worktree state changed after the latest checkpoint", validate_root(task_root))

    def test_complete_local_feature_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repository"
            task_root = root / "task"
            repository.mkdir()
            task_root.mkdir()
            subprocess.run(["git", "init", "-q", str(repository)], check=True)
            subprocess.run(["git", "-C", str(repository), "config", "user.name", "Factory Test"], check=True)
            subprocess.run(["git", "-C", str(repository), "config", "user.email", "factory@example.test"], check=True)
            (repository / "feature.txt").write_text("before\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repository), "add", "feature.txt"], check=True)
            subprocess.run(["git", "-C", str(repository), "commit", "-q", "-m", "Initial state"], check=True)
            base = subprocess.run(
                ["git", "-C", str(repository), "rev-parse", "HEAD"],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()

            (task_root / "task.json").write_text(json.dumps(task(repository)), encoding="utf-8")
            (task_root / "report.md").write_text("# Intake\n\nAligned.\n", encoding="utf-8")
            intake = run_checkpoint(task_root, "INTAKE", "aligned")
            self.assertEqual("TRIAGE", json.loads(intake.stdout)["next_lifecycle"])

            current_assurance = assurance(base_revision=base, change_revision=None)
            (task_root / "assurance.json").write_text(json.dumps(current_assurance), encoding="utf-8")
            (task_root / "report.md").write_text("# Triage\n\nReady.\n", encoding="utf-8")
            triage = run_checkpoint(task_root, "TRIAGE", "ready")
            self.assertEqual("IMPLEMENTATION", json.loads(triage.stdout)["next_lifecycle"])

            (repository / "feature.txt").write_text("after\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repository), "add", "feature.txt"], check=True)
            subprocess.run(["git", "-C", str(repository), "commit", "-q", "-m", "Add feature"], check=True)
            head = subprocess.run(
                ["git", "-C", str(repository), "rev-parse", "HEAD"],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
            current_assurance["change_revision"] = head
            current_assurance["diff_groups"] = [{"id": "diff-1", "path": "path-1"}]
            (task_root / "assurance.json").write_text(json.dumps(current_assurance), encoding="utf-8")
            (task_root / "report.md").write_text("# Implementation\n\nCommitted.\n", encoding="utf-8")
            implementation = run_checkpoint(task_root, "IMPLEMENTATION", "complete")
            self.assertEqual("CHANGE_ASSURANCE", json.loads(implementation.stdout)["next_lifecycle"])

            current_assurance["verdict"] = "pass"
            current_assurance["evidence"] = [{"id": "evidence-1", "revision": head, "result": "pass"}]
            (task_root / "assurance.json").write_text(json.dumps(current_assurance), encoding="utf-8")
            (task_root / "report.md").write_text("# Change assurance\n\nPassed.\n", encoding="utf-8")
            assured = run_checkpoint(task_root, "CHANGE_ASSURANCE", "pass")
            self.assertEqual("COMPLETED", json.loads(assured.stdout)["next_lifecycle"])

            (task_root / "report.md").write_text("# Complete\n\nThe local commit is assured.\n", encoding="utf-8")
            completed = run_checkpoint(task_root, "COMPLETED", "complete")
            self.assertIsNone(json.loads(completed.stdout)["next_lifecycle"])
            self.assertEqual([], validate_root(task_root))


if __name__ == "__main__":
    unittest.main()
