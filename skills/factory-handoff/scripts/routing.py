"""Deterministic guarded routing for the compact Factory lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Decision:
    next_lifecycle: str | None
    stop: bool
    reason: str
    resume_lifecycle: str | None = None


def authority_allows(task: dict[str, Any], *actions: str) -> bool:
    authority = task.get("authority", {})
    return all(authority.get(action) is True for action in actions)


def correction_count(history: list[dict[str, Any]], lifecycle: str, target: str) -> int:
    return sum(
        record.get("lifecycle") == lifecycle
        and record.get("next_lifecycle") == target
        for record in history
    )


def decide(
    task: dict[str, Any],
    assurance: dict[str, Any] | None,
    history: list[dict[str, Any]],
    lifecycle: str,
    outcome: str,
    *,
    git_head: str | None = None,
    worktree_dirty: bool | None = None,
) -> Decision:
    if lifecycle == "CANCELLED":
        return Decision(None, True, "The task is cancelled.")
    if lifecycle == "COMPLETED":
        return Decision(None, True, "The requested deliverable is complete.")

    routing = (assurance or {}).get("routing", {})
    stop_flags = [
        "decision_required",
        "scope_changed",
        "risk_changed",
        "required_dependency_unavailable",
    ]
    if task.get("status") == "needs_input" or task.get("open_decisions"):
        return Decision("AWAITING_INPUT", True, "The task contract needs human input.", lifecycle)
    if any(routing.get(flag) is True for flag in stop_flags):
        return Decision("AWAITING_INPUT", True, "Current evidence passes a human stop gate.", lifecycle)

    normalized = outcome.replace("-", "_").casefold()
    if lifecycle == "INTAKE":
        if normalized == "aligned":
            return Decision("TRIAGE", False, "The task contract is aligned.")
        return Decision("AWAITING_INPUT", True, "Intake did not align the task contract.", "INTAKE")

    if lifecycle == "TRIAGE":
        if normalized != "ready":
            return Decision("AWAITING_INPUT", True, "Triage did not produce a ready change packet.", "TRIAGE")
        if not assurance or not assurance.get("paths"):
            return Decision("AWAITING_INPUT", True, "Triage did not provide complete assurance paths.", "TRIAGE")
        if assurance and assurance.get("plan_assurance_required") is True:
            return Decision("PLAN_ASSURANCE", False, "Triage requires independent plan assurance.")
        if not authority_allows(task, "edit", "test", "commit"):
            return Decision("AWAITING_INPUT", True, "Implementation authority is incomplete.", "IMPLEMENTATION")
        return Decision("IMPLEMENTATION", False, "Triage produced an implementation-ready change packet.")

    if lifecycle == "PLAN_ASSURANCE":
        if normalized == "approve" and assurance and assurance.get("verdict") == "plan_approved":
            if not authority_allows(task, "edit", "test", "commit"):
                return Decision("AWAITING_INPUT", True, "Implementation authority is incomplete.", "IMPLEMENTATION")
            return Decision("IMPLEMENTATION", False, "Independent plan assurance approved the plan.")
        if normalized == "reject" and assurance and assurance.get("verdict") == "plan_rejected":
            if correction_count(history, "PLAN_ASSURANCE", "TRIAGE") >= 1:
                return Decision("AWAITING_INPUT", True, "One automatic triage correction did not resolve plan findings.", "TRIAGE")
            return Decision("TRIAGE", False, "Plan assurance found a triage defect.")
        return Decision("AWAITING_INPUT", True, "Plan assurance needs input or required evidence.", "PLAN_ASSURANCE")

    if lifecycle == "IMPLEMENTATION":
        if normalized == "complete":
            if not assurance or not assurance.get("change_revision"):
                return Decision("AWAITING_INPUT", True, "Implementation did not provide a committed revision.", "IMPLEMENTATION")
            if worktree_dirty is not False or git_head != assurance.get("change_revision"):
                return Decision("AWAITING_INPUT", True, "Implementation did not leave the exact committed revision clean.", "IMPLEMENTATION")
            return Decision("CHANGE_ASSURANCE", False, "Implementation produced a committed revision.")
        return Decision("AWAITING_INPUT", True, "Implementation needs input or required evidence.", "IMPLEMENTATION")

    if lifecycle == "CHANGE_ASSURANCE":
        if normalized == "pass" and assurance and assurance.get("verdict") == "pass":
            if worktree_dirty is not False or git_head != assurance.get("change_revision"):
                return Decision("AWAITING_INPUT", True, "Assurance does not match the clean branch head.", "CHANGE_ASSURANCE")
            if task.get("deliverable") == "draft_pull_request":
                if not authority_allows(task, "push", "draft_pull_request"):
                    return Decision("AWAITING_INPUT", True, "Delivery authority is incomplete.", "DELIVERY")
                return Decision("DELIVERY", False, "The exact commit passed independent assurance.")
            return Decision("COMPLETED", False, "The requested local commit passed independent assurance.")
        if normalized == "fail" and assurance and assurance.get("verdict") == "fail":
            if correction_count(history, "CHANGE_ASSURANCE", "IMPLEMENTATION") >= 1:
                return Decision("AWAITING_INPUT", True, "One automatic correction did not resolve assurance findings.", "IMPLEMENTATION")
            return Decision("IMPLEMENTATION", False, "Change assurance found an implementation defect.")
        return Decision("AWAITING_INPUT", True, "Change assurance needs input or required evidence.", "CHANGE_ASSURANCE")

    if lifecycle == "DELIVERY":
        if normalized == "published" and assurance and assurance.get("verdict") == "pass":
            if worktree_dirty is not False or git_head != assurance.get("change_revision"):
                return Decision("AWAITING_INPUT", True, "Delivery does not match the assured clean branch head.", "DELIVERY")
            return Decision("COMPLETED", False, "The assured commit was published as requested.")
        return Decision("AWAITING_INPUT", True, "Delivery did not publish the requested draft pull request.", "DELIVERY")

    if lifecycle == "AWAITING_INPUT":
        if normalized != "resolved" or not history:
            return Decision("AWAITING_INPUT", True, "The required human input is not resolved.")
        resume_lifecycle = history[-1].get("resume_lifecycle")
        if not resume_lifecycle:
            return Decision("AWAITING_INPUT", True, "The paused task has no safe resume lifecycle.")
        return Decision(str(resume_lifecycle), False, "The required human input is resolved.")

    return Decision("AWAITING_INPUT", True, "The current lifecycle has no valid route.", lifecycle)
