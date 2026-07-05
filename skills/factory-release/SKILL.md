---
name: factory-release
description: "Use after review to prepare a software-factory change for human approval, merge, release notes, deployment awareness, rollback planning, and post-merge observation."
---

# Factory Release

Use this skill when a change appears ready and the human needs a merge decision
packet.

## Workflow

1. Do not modify files unless explicitly asked.
2. Read the task, plan, implementation summary, verification results, review
   findings, and current branch state.
3. Spawn `release-manager`.
4. Keep the subagent read-only.
5. Synthesize a concise human approval packet.

## Readiness Criteria

- Acceptance criteria are satisfied.
- Required verification passed or exceptions are explicit.
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
