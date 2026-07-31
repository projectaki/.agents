---
name: factory-implement
description: "Use only when the human explicitly starts implementation with an approved plan, scoped repository or worktree, acceptance criteria, and required decisions. Implement that scope, add targeted tests, account for the working diff, and return an implementation packet."
---

# Factory Implement

Implement only the approved plan.

When orchestrated, the primary thread must delegate this skill to the routed
tier worker. That worker owns the implementation and must not spawn another
lifecycle actor.

## Inputs

Require an approved plan, repository or worktree, acceptance criteria, required
decisions, and a replication baseline for bug fixes. Stop before editing if a
required input is missing.

## Workflow

1. Confirm approval and inspect Git status. Preserve user changes.
2. Implement the approved scope with repository patterns. Avoid unrelated
   refactors and keep domain logic out of infrastructure.
3. Add the smallest useful tests mapped to plan risk IDs. Add a practical
   regression test for deterministic bugs.
4. Create or update the canonical `change-assurance-report.md`. Group the whole
   working diff, map every group to behavioral paths or a precise
   non-behavioral classification, and record current evidence.
5. Run reachable targeted checks.
6. Return the implementation packet and remaining verification work.

Investigate failed checks; treat unrun checks as unknown. Report inaccessible
required checks. If evidence invalidates the plan, request a revision instead
of expanding scope.

For optional tools, check availability once and try once. Do not install tools
or seek elevated access only to run them.

## Output

Return an agent packet with:

- changed files and behavior
- complete working-diff accountability in the current assurance report
- tests mapped to risk IDs
- commands, results, and exact covered head or diff
- skipped checks, fallbacks, uncovered risk IDs, and residual risk
- unimplemented scope, unresolved risks, and required decisions

When orchestrated, also write one plain-language `report.md`: what changed,
what did not, checks run, current risks, and readiness. Keep internal IDs,
fingerprints, and exhaustive mappings in the assurance report. Follow the
shared pattern in `../factory-handoff/references/human-report-patterns.md` and
use its Implementation guidance.

Describe only current state. Mention plan divergence only when it leaves active
scope, risk, or a decision. Stop when the approved scope and targeted tests are
complete or blocked. Do not review, verify, or start another lifecycle.
