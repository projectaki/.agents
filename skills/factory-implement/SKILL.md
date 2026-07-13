---
name: factory-implement
description: "Use after human approval of a plan to implement a scoped software-factory change in the current Codex thread or worktree, add targeted tests, and prepare an implementation summary."
disable-model-invocation: true
---

# Factory Implement

Use this skill only after the plan is approved.

## Workflow

1. Confirm the plan is approved.
2. Inspect the current git status before editing.
3. Implement in the main Codex thread by default.
4. Use Codex's built-in `worker` agent only when the task is large enough to
   justify delegated implementation.
5. Keep edits scoped to the approved plan.
6. Add or update the smallest useful tests.
7. Run the targeted checks that are cheap and directly relevant.
8. Summarize changes and remaining verification needs.

## Implementation Rules

- Do not perform unrelated refactors.
- Do not change architecture outside the approved plan.
- Preserve user changes in the working tree.
- Prefer existing patterns and local helper APIs.
- Keep domain logic out of infrastructure.
- Treat failed checks as work to investigate, not noise to ignore.

## Output

Return:

- files changed
- behavior changed
- tests added or updated
- commands run and results
- deviations from the approved plan
- unresolved risks
- next verification step

If implementation reveals the approved plan is wrong, stop and ask for a plan
revision instead of improvising a broad fix.
