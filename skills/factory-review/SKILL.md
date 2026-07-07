---
name: factory-review
description: "Use after implementation and verification to review a branch or diff for correctness, simplicity, maintainability, test coverage, architecture fit, security, privacy, and operational risk before human approval."
---

# Factory Review

Use this skill after implementation has been verified enough to review.

## Workflow

1. Compare the branch or worktree against the intended base branch.
2. Spawn `maintainability-reviewer`.
3. Spawn `security-reviewer`.
4. Spawn `verification-engineer` when verification evidence is incomplete or
   needs an independent check.
5. Add `user-simulator` for user-facing changes or missing visual evidence.
6. Wait for all subagents.
7. Synthesize findings in the main thread.

## Review Rules

- Lead with bugs, regressions, security issues, missing tests, and architecture
  problems.
- Order findings by severity: P0, P1, P2, P3.
- Cite files and line numbers when possible.
- Do not request unrelated refactors.
- If no blocking issues are found, say that clearly and name residual risk.
- For web UI changes, prefer Playwright screenshot/snapshot evidence.
- For iOS simulator checks, only attempt simulator access on macOS (`Darwin`).

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
