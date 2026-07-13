---
name: factory-implement
description: "Use only when the human explicitly starts the implementation lifecycle with an approved plan, scoped repository or worktree, and required decisions, to implement that scope, add targeted tests, and produce an implementation packet."
disable-model-invocation: true
---

# Factory Implement

Use this skill only after the plan is approved.

## Input

Require a human-approved plan, the repository or worktree in scope, acceptance
criteria, and any decisions or authority required by the plan. For a bug fix,
also require the applicable replication baseline. If approval or required input
is missing, stop without editing files and return the gap.

## Environment Policy

- Implement in the main session by default. Delegate a bounded part only when
  delegation is authorized by the user and repository policy, suitable
  subagents are available, and the task benefits from delegation.
- If delegation is unauthorized, unavailable, or lacks required execution
  capabilities, continue in an authorized capable session.
- Treat browser, simulator, device, GUI, network, and other access-controlled
  tools as conditional. Make at most one cheap availability check and one
  ordinary attempt when a planned optional check needs them.
- After a missing-tool or clear permission, sandbox, launch, or access-control
  failure, stop retrying. Do not install tools or seek elevated access solely
  for an optional check. Record the skip, fallback evidence, and residual risk.

## Workflow

1. Confirm the plan is approved.
2. Inspect current git status and preserve existing user changes.
3. Implement only the approved scope.
4. Add or update the smallest useful tests.
5. Run cheap, targeted checks that are reachable in the environment.
6. Summarize changes and remaining verification needs.

For a bug fix, preserve the replicated baseline, implement the smallest fix,
and add a regression test when the behavior is deterministic and testable.

## Implementation Rules

- Do not perform unrelated refactors or change architecture outside the plan.
- Prefer existing patterns and local helper APIs.
- Keep domain logic out of infrastructure.
- Treat failed checks as work to investigate, not noise.
- Treat unrun checks as unknown. If a required check is inaccessible, stop and
  report the blocker instead of claiming completion.
- If replication evidence invalidates the plan, request a plan revision rather
  than expanding implementation into broad diagnosis.

## Output

Return:

- files and behavior changed
- tests added or updated
- commands or methods run and results
- skipped checks, reasons, fallbacks, and residual risk
- deviations from the approved plan
- unresolved risks
- decisions or remaining work requiring human action

## Stop Condition

Stop when the approved implementation scope and targeted tests are complete and
the implementation packet is ready, or when the plan is invalidated or a
required decision blocks safe progress. Return the packet to the human. Do not
invoke verification, review, or another factory skill and do not start another
lifecycle.
