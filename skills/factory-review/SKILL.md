---
name: factory-review
description: "Use after implementation and verification to review a branch or diff for correctness, simplicity, maintainability, test coverage, architecture fit, security, privacy, and operational risk before human approval."
---

# Factory Review

Use this skill after implementation has been verified enough to review.

## Workflow

1. Do not edit files during review.
2. Compare the branch or worktree against the intended base branch.
3. Spawn `maintainability-reviewer`.
4. Spawn `security-reviewer`.
5. Spawn `verification-engineer` when verification evidence is incomplete or
   needs an independent check.
6. Add `user-simulator` for user-facing changes.
7. Wait for all subagents.
8. Synthesize findings in the main thread.

## Review Rules

- Lead with bugs, regressions, security issues, missing tests, and architecture
  problems.
- Order findings by severity: P0, P1, P2, P3.
- Cite files and line numbers when possible.
- Do not request unrelated refactors.
- If no blocking issues are found, say that clearly and name residual risk.

## Output

Return:

- review verdict: approve, approve-with-changes, reject, or blocked
- findings ordered by severity
- missing tests or verification
- security and privacy concerns
- maintainability concerns
- required fixes before merge
- residual risk

P0 and P1 findings must be fixed, explicitly rejected with rationale, or
escalated to the human orchestrator.
