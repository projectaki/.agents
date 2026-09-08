"""Evidence required before consequential Factory actions."""

from __future__ import annotations

import hashlib
import json

from records import validate_acceptance, validate_assurance


def plan_fingerprint(assurance):
    fields = ("task_revision", "assessment", "steps", "paths", "risks", "signals",
              "sensitive_change", "plan_assurance_required")
    plan = {field: assurance.get(field) for field in fields}
    plan["exceptions"] = [{key: item.get(key) for key in ("id", "behavior", "approval", "residual_risk")}
                          for item in assurance.get("exceptions", []) if isinstance(item, dict)]
    plan["proof"] = [{key: item.get(key) for key in ("id", "proof")}
                     for item in assurance.get("evidence", [])]
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()


def current_history(task, history):
    start = max((i + 1 for i, item in enumerate(history)
                 if item.get("outcome") == "reopened"), default=0)
    return [item for item in history[start:]
            if item.get("task_revision") == task.get("task_revision")]


def implementation_record(task, history, head, base):
    return next((item for item in reversed(current_history(task, history))
                 if item.get("lifecycle") == "IMPLEMENTATION"
                 and item.get("outcome") == "complete"
                 and (item.get("next_lifecycle") == "CHANGE_ASSURANCE"
                      or item.get("next_lifecycle") == "AWAITING_INPUT" and item.get("resume_lifecycle") == "CHANGE_ASSURANCE")
                 and item.get("git_head") == head and item.get("git_base") == base), None)


def independent_review(task, history, head, base, assurance):
    implementation = implementation_record(task, history, head, base)
    if not implementation or not implementation.get("worker_id"):
        return False
    owners = {item.get("worker_id") for item in current_history(task, history)
              if item.get("lifecycle") == "IMPLEMENTATION" and item.get("worker_id")}
    later = current_history(task, history)
    later = later[later.index(implementation) + 1:]
    reviews = [item for item in later if item.get("lifecycle") == "CHANGE_ASSURANCE"
               and item.get("git_head") == head and item.get("git_base") == base]
    if not reviews:
        return False
    review = reviews[-1]
    accepted = (review.get("next_lifecycle") in {"DELIVERY", "COMPLETED"}
                or review.get("next_lifecycle") == "AWAITING_INPUT"
                and review.get("resume_lifecycle") in {"DELIVERY", "COMPLETED"})
    return (review.get("outcome") == "pass" and accepted and bool(review.get("worker_id"))
            and review["worker_id"] not in owners
            and review.get("plan_fingerprint") == plan_fingerprint(assurance))


def prerequisite_errors(task, assurance, history, target, *, worker_id=None,
                        git_head=None, git_base=None, git_branch=None, worktree_dirty=None, files=None):
    if target in {"INTAKE", "TRIAGE", "AWAITING_INPUT", "CANCELLED", None}:
        return []
    errors = []
    if task.get("status") != "aligned" or task.get("open_decisions"):
        errors.append("Resolve the task's material decisions before this action.")
    if not assurance:
        return [*errors, "Inspect the repository and record the relevant behavior and risks first."]
    if any(assurance.get("routing", {}).get(flag) for flag in
           ("decision_required", "scope_changed", "risk_changed", "required_dependency_unavailable")):
        errors.append("Resolve the recorded decision, scope, or dependency blocker first.")
    errors.extend(validate_assurance(assurance, task["task_revision"]))
    if errors:
        return errors
    if target in {"PLAN_ASSURANCE", "IMPLEMENTATION"}:
        if not isinstance(assurance.get("assessment"), str) or not assurance["assessment"].strip():
            errors.append("Record the repository findings that support the risk assessment.")
        behaviors = {item["behavior"] for item in assurance["paths"] if isinstance(item, dict) and isinstance(item.get("behavior"), str)}
        if not set(task["acceptance_criteria"]).issubset(behaviors):
            errors.append("Map each acceptance criterion to planned proof before implementation.")
        evidence = {item["id"] for item in assurance["evidence"] if isinstance(item.get("id"), str)}
        for item in assurance["paths"] + assurance["risks"]:
            if not isinstance(item, dict) or not isinstance(item.get("behavior"), str) or not item["behavior"].strip():
                errors.append("Each behavior and material risk needs a description.")
                continue
            refs = item.get("evidence", [])
            if not refs:
                exception = next((entry for entry in assurance["exceptions"] if isinstance(entry, dict)
                                  and entry.get("id") == item.get("exception")
                                  and entry.get("behavior") == item["behavior"]), {})
                if not all(isinstance(exception.get(key), str) and exception[key].strip()
                           for key in ("approval", "residual_risk")):
                    errors.append("Each behavior and material risk needs planned proof or an accepted exception.")
            elif not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in evidence for ref in refs):
                errors.append("Planned proof references must exist.")
        if assurance["blockers"]:
            errors.append("Resolve dependent work's blockers before implementation.")
    if target == "IMPLEMENTATION":
        if not all(task["authority"].get(action) for action in ("edit", "test", "commit")):
            errors.append("Implementation authority is incomplete.")
        if assurance["plan_assurance_required"]:
            approvals = [item for item in current_history(task, history)
                         if item.get("lifecycle") == "PLAN_ASSURANCE"]
            approved = approvals[-1] if approvals else {}
            if (approved.get("outcome") != "approve"
                    or approved.get("plan_fingerprint") != plan_fingerprint(assurance)
                    or not approved.get("worker_id")
                    or worker_id is not None and approved["worker_id"] == worker_id):
                errors.append("The current plan needs independent approval before implementation.")
    if target in {"CHANGE_ASSURANCE", "DELIVERY", "COMPLETED"}:
        if (not git_head or assurance.get("change_revision") != git_head
                or not git_base or assurance.get("base_revision") != git_base
                or not git_branch or assurance.get("branch") != git_branch
                or worktree_dirty is not False):
            errors.append("Assurance must match the current clean head, base, and branch.")
        errors.extend(validate_acceptance(task, assurance, files))
    if target == "CHANGE_ASSURANCE":
        implementation = implementation_record(task, history, git_head, git_base)
        if not implementation or not implementation.get("worker_id"):
            errors.append("Record the implementation and its worker identity before review.")
        elif worker_id is not None and any(item.get("lifecycle") == "IMPLEMENTATION"
                                          and item.get("worker_id") == worker_id
                                          for item in current_history(task, history)):
            errors.append("The reviewer must be independent from the implementer.")
    if target in {"DELIVERY", "COMPLETED"}:
        if assurance["verdict"] != "pass" or assurance["blockers"]:
            errors.append("Passing change assurance without blockers is required.")
        if not independent_review(task, history, git_head, git_base, assurance):
            errors.append("The current revision needs a recorded independent review.")
    if target == "DELIVERY" and not all(task["authority"].get(action) for action in ("push", "draft_pull_request")):
        errors.append("Delivery authority is incomplete.")
    return errors
