---
name: factory-implement
description: "Use only when the human explicitly starts the implementation lifecycle with an approved plan, scoped repository or worktree, acceptance criteria, and required decisions. Implement that scope, add targeted tests, account for the working diff in the change-assurance report, and return an implementation packet."
---

# Factory Implement

## Execution boundary

When used by the orchestrator, the primary thread must spawn the tier worker
selected by routing and instruct that worker to use this skill. The primary
thread must not perform this lifecycle workflow. A tier worker executes the
workflow directly and does not spawn another lifecycle actor.

Implement an approved plan and nothing more.

## Need

An approved plan, repository or worktree, acceptance criteria, required
decisions, and the replication baseline for a bug fix. If anything required is
missing, stop before editing.

## Do

1. Confirm approval and inspect git status. Preserve existing user changes.
2. Implement only the approved scope using repository patterns.
3. Add or update the smallest useful tests mapped to the plan's risk IDs. For a
   deterministic bug, add a regression test when practical.
4. Create or update the canonical `change-assurance-report.md` defined by the
   orchestrator. Group the complete working diff into stable change groups,
   map each group to behavioral paths or a precise non-behavioral
   classification, and record current evidence.
5. Run reachable targeted checks.
6. Return the implementation packet and remaining verification work.

Keep domain logic out of infrastructure and avoid unrelated refactors. Treat
failed checks as work to investigate and unrun checks as unknown. If a required
check is inaccessible, report the blocker. If evidence invalidates the plan,
request a plan revision instead of expanding scope.

Do not spawn nested implementation agents. The selected tier worker owns the
bounded implementation assignment. For optional conditional tools, make one
availability check and one attempt; do not install tools or seek elevated
access solely to run them.

## Return

Return the agent-oriented implementation packet with:

- files and behavior changed
- current change-assurance report with complete working-diff accountability
- tests added or updated, mapped to risk IDs
- commands run, results, and the exact head or diff they cover
- skipped checks, fallbacks, and residual risk
- risk IDs without automated coverage and the reason
- current scope not implemented, unresolved risks, and decisions still needed

When used by the orchestrator, also provide the lifecycle's single human
`report.md`. Describe what changed, what remains unchanged, checks already run,
current risks, and readiness in plain language. Keep diff group IDs, path IDs,
evidence IDs, fingerprints, and exhaustive accountability in the internal
change-assurance report.

Write the packet as the current implementation state. Do not narrate earlier
attempts, corrected mistakes, or superseded plan details. Mention a divergence
from the approved plan only when it leaves a current scope, risk, or decision
that the next lifecycle must handle.

## Stop

Return the implementation packet when the approved scope and targeted tests are
complete, or when blocked. Do not verify, review, or start another lifecycle.
