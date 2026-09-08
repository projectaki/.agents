"""Deterministic guarded routing for the compact Factory lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from records import validate_acceptance
from prerequisites import independent_review, prerequisite_errors, plan_fingerprint


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
    reopened = [index for index, record in enumerate(history) if record.get("outcome") == "reopened" and record.get("next_lifecycle") in {"TRIAGE", "IMPLEMENTATION"}]
    if reopened:
        history = history[reopened[-1] + 1:]
    return sum(
        record.get("lifecycle") == lifecycle
        and record.get("next_lifecycle") == target
        for record in history
    )


def default_route(
    task: dict[str, Any],
    assurance: dict[str, Any] | None,
    history: list[dict[str, Any]],
    lifecycle: str,
    outcome: str,
    *,
    git_head: str | None = None,
    worktree_dirty: bool | None = None,
    git_base: str | None = None,
    git_branch: str | None = None,
    files: list[str] | None = None,
) -> Decision:
    if lifecycle == "CANCELLED":
        return Decision(None, True, "The task is cancelled.")

    routing = (assurance or {}).get("routing", {})
    stop_flags = [
        "decision_required",
        "scope_changed",
        "required_dependency_unavailable",
    ]
    if task.get("status") == "needs_input" or task.get("open_decisions"):
        return Decision("AWAITING_INPUT", True, "The task contract needs human input.", lifecycle)
    if any(routing.get(flag) is True for flag in stop_flags):
        return Decision("AWAITING_INPUT", True, "Current evidence passes a human stop gate.", lifecycle)

    normalized = outcome.replace("-", "_").casefold()
    if lifecycle == "COMPLETED" and normalized == "reopened":
        deliveries = [record for record in history if record.get("lifecycle") == "COMPLETED" and record.get("status") == "terminal"]
        if not deliveries:
            return Decision("AWAITING_INPUT", True, "Reopening requires an earlier completed delivery.", "TRIAGE")
        if not authority_allows(task, "edit", "test", "commit"):
            return Decision("AWAITING_INPUT", True, "Follow-up implementation authority is incomplete.", "IMPLEMENTATION")
        if not assurance or assurance.get("verdict") != "unverified":
            return Decision("AWAITING_INPUT", True, "Reset assurance before reopening authorized work.", "TRIAGE")
        target = "TRIAGE" if task.get("task_revision") != deliveries[-1].get("task_revision") else "IMPLEMENTATION"
        return Decision(target, False, "Authorized follow-up work reopened the task.")

    if routing.get("risk_changed"):
        return Decision("TRIAGE", False, "Reassess the changed risk before dependent work.")

    accepting = (
        lifecycle == "COMPLETED"
        or lifecycle == "IMPLEMENTATION" and normalized == "complete"
        or lifecycle == "CHANGE_ASSURANCE" and normalized == "pass"
        or lifecycle == "DELIVERY" and normalized == "published"
    )
    if accepting:
        if (
            not assurance
            or assurance.get("task_revision") != task.get("task_revision")
            or not git_head or git_head != assurance.get("change_revision")
            or not git_base or git_base != assurance.get("base_revision")
            or not git_branch or git_branch != assurance.get("branch")
            or worktree_dirty is not False
        ):
            return Decision("IMPLEMENTATION", False, "The task, head, base, branch, or clean worktree does not match assurance.")
        errors = validate_acceptance(task, assurance, files)
        if errors:
            return Decision("IMPLEMENTATION", False, "; ".join(errors))
        if lifecycle != "IMPLEMENTATION" and (assurance.get("verdict") != "pass" or assurance.get("blockers")):
            return Decision("CHANGE_ASSURANCE", False, "Completion requires passing assurance without blockers.")

    if lifecycle == "COMPLETED":
        if not independent_review(task, history, git_head, git_base, assurance):
            return Decision("CHANGE_ASSURANCE", False, "The current revision needs a recorded independent review.")
        if task.get("deliverable") == "draft_pull_request" and not any(
            record.get("lifecycle") == "DELIVERY"
            and record.get("outcome") == "published"
            and record.get("next_lifecycle") == "COMPLETED"
            and record.get("git_head") == git_head
            and record.get("git_base") == git_base
            and record.get("task_revision") == task.get("task_revision")
            for record in history
        ):
            if not authority_allows(task, "push", "draft_pull_request"):
                return Decision("AWAITING_INPUT", True, "Delivery authority is incomplete.", "DELIVERY")
            return Decision("DELIVERY", False, "The current revision has no successful delivery record.")
        return Decision(None, True, "The requested deliverable is complete for the current revision.")

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
        if normalized == "needs_triage":
            return Decision("TRIAGE", False, "New evidence requires further investigation.")
        if normalized == "in_progress":
            return Decision("IMPLEMENTATION", False, "A bounded part is complete; accepted behavior remains.")
        if normalized == "complete":
            return Decision("CHANGE_ASSURANCE", False, "Implementation produced a committed revision.")
        return Decision("AWAITING_INPUT", True, "Implementation needs input or required evidence.", "IMPLEMENTATION")

    if lifecycle == "CHANGE_ASSURANCE":
        if normalized == "needs_triage":
            return Decision("TRIAGE", False, "Review found an assumption that needs investigation.")
        if normalized == "pass" and assurance and assurance.get("verdict") == "pass":
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


def select_route(task, assurance, history, lifecycle, outcome, *, proposed_next=None,
                 route_reason=None, worker_id=None, **facts):
    normalized = outcome.replace("-", "_").casefold()
    decision = default_route(task, assurance, history, lifecycle, outcome, **facts)
    if decision.stop or lifecycle == "COMPLETED":
        return decision
    if lifecycle == "IMPLEMENTATION" and normalized == "complete":
        errors = prerequisite_errors(task, assurance, history, "IMPLEMENTATION", worker_id=worker_id)
        if errors:
            return Decision("TRIAGE", False, "; ".join(errors))
    if lifecycle == "CHANGE_ASSURANCE" and normalized == "pass":
        errors = prerequisite_errors(task, assurance, history, "CHANGE_ASSURANCE", worker_id=worker_id, **facts)
        if not worker_id:
            errors.append("Record the review worker identity.")
        if errors:
            return Decision("CHANGE_ASSURANCE", False, "; ".join(errors))
    if lifecycle == "DELIVERY" and normalized == "published":
        errors = prerequisite_errors(task, assurance, history, "DELIVERY", **facts)
        if errors:
            return Decision("CHANGE_ASSURANCE", False, "; ".join(errors))
    if proposed_next is None:
        return decision
    if not route_reason or not route_reason.strip():
        raise ValueError("A proposed next stage requires a concrete route reason")
    if proposed_next not in {"INTAKE", "TRIAGE", "PLAN_ASSURANCE", "IMPLEMENTATION", "CHANGE_ASSURANCE", "DELIVERY", "COMPLETED"}:
        raise ValueError("Unsupported proposed next stage")
    provisional = {"lifecycle": lifecycle, "outcome": normalized,
                   "next_lifecycle": decision.next_lifecycle, "task_revision": task["task_revision"],
                   "worker_id": worker_id, "git_head": facts.get("git_head"),
                   "git_base": facts.get("git_base"), "plan_fingerprint": plan_fingerprint(assurance or {})}
    errors = prerequisite_errors(task, assurance, [*history, provisional], proposed_next, **facts)
    if errors:
        raise ValueError("Proposed stage prerequisites: " + "; ".join(errors))
    return Decision(proposed_next, False, route_reason.strip())


def decide(task, assurance, history, lifecycle, outcome, *, run_id=None,
           active_seconds=None, progress=None, **options):
    decision = select_route(task, assurance, history, lifecycle, outcome, **options)
    if decision.stop or lifecycle == "COMPLETED":
        return decision
    if task.get("continuation_mode") == "automatic" and run_id:
        run = [item for item in history if item.get("run_id") == run_id]
        elapsed = sum(item.get("active_seconds") or 0 for item in run) + (active_seconds or 0)
        if elapsed >= 1800:
            return Decision("AWAITING_INPUT", True, "Automatic work reached 30 minutes of active execution.", decision.next_lifecycle)
        if progress is False and run and run[-1].get("progress") is False:
            return Decision("AWAITING_INPUT", True, "Two consecutive assignments made no material progress.", decision.next_lifecycle)
    return decision
