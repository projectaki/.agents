---
name: factory-implement
description: "Use only when the human explicitly starts the implementation lifecycle with an approved plan, scoped repository or worktree, acceptance criteria, and required decisions. Implement that scope, add targeted tests, and return an implementation packet."
---

# Factory Implement

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
4. Run reachable targeted checks.
5. Return the implementation packet and remaining verification work.

Keep domain logic out of infrastructure and avoid unrelated refactors. Treat
failed checks as work to investigate and unrun checks as unknown. If a required
check is inaccessible, report the blocker. If evidence invalidates the plan,
request a plan revision instead of expanding scope.

Spawn subagents for bounded implementation steps only when useful and allowed by
repository policy. For optional conditional tools, make one availability check
and one attempt; do not install tools or seek elevated access solely to run them.

## Return

- files and behavior changed
- tests added or updated, mapped to risk IDs
- commands run, results, and the exact head or diff they cover
- skipped checks, fallbacks, and residual risk
- risk IDs without automated coverage and the reason
- current scope not implemented, unresolved risks, and decisions still needed

Write the packet as the current implementation state. Do not narrate earlier
attempts, corrected mistakes, or superseded plan details. Mention a divergence
from the approved plan only when it leaves a current scope, risk, or decision
that the next lifecycle must handle.

## Stop

Return the implementation packet when the approved scope and targeted tests are
complete, or when blocked. Do not verify, review, or start another lifecycle.
