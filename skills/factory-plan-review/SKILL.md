---
name: factory-plan-review
description: "Use before implementation to review a proposed software-factory plan for scope, simplicity, architecture fit, missing verification, security risk, and unresolved assumptions."
---

# Factory Plan Review

Use this skill after a plan exists and before code changes begin.

## Workflow

1. Do not edit files.
2. Spawn `plan-reviewer` and `verification-engineer`.
3. Add `security-reviewer` for auth, authorization, data, secrets, migrations,
   infrastructure, dependencies, external integrations, or high-risk changes.
4. Add `maintainability-reviewer` when the plan touches shared code or
   architecture.
5. Keep all subagents read-only.
6. Wait for all subagents.
7. Synthesize findings in the main thread.

## Review Criteria

- Is the task ready enough to implement?
- Is the plan the smallest safe change?
- Does the plan respect architecture and repo conventions?
- Are tests and verification strong enough?
- Are security, privacy, operational, or migration risks addressed?
- Are assumptions and human decisions explicit?

## Output

Return:

- verdict: approve, approve-with-changes, reject, or blocked
- blocking findings ordered by severity
- missing acceptance criteria
- missing verification
- security or operational concerns
- recommended plan changes
- human approval questions

Do not proceed to implementation when the verdict is reject or blocked.
