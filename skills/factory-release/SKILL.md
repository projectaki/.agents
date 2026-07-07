---
name: factory-release
description: "Use after review to prepare a software-factory change for human approval, merge, release notes, deployment awareness, rollback planning, and post-merge observation."
---

# Factory Release

Use this skill when a change appears ready and the human needs a merge decision
packet.

## Workflow

1. Read the task, plan, implementation summary, verification results, review
   findings, and current branch state.
2. Spawn `release-manager`.
3. Synthesize a concise human approval packet.

## Readiness Criteria

- Acceptance criteria are satisfied.
- Required verification passed or exceptions are explicit.
- Visual evidence exists for user-facing changes or the exception is explicit.
- Blocking review findings are resolved or escalated.
- Release notes exist when user-visible behavior changed.
- Migration, deployment, rollback, and observation concerns are addressed when
  relevant.
- Residual risk is clear enough for a human decision.

## Output

Return:

- merge readiness verdict: ready, not-ready, blocked, or human-risk-decision
- change summary
- verification summary
- review summary
- unresolved risks
- release notes draft if relevant
- rollback or recovery notes if relevant
- post-merge observation steps
- exact human decision needed
