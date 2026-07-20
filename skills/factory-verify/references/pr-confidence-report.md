# PR Verification Report

## Summary

- **Why:** <intended outcome>
- **Changed:** <implemented behavior>
- **Affected:** <users, systems, contracts, data, and operations>

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| <criterion> | Pass/Fail/Unverified | <implementation and observed proof> |

## UI workflow evidence

| ID | Workflow | Result | Video |
|---|---|---|---|
| <workflow ID> | <workflow title> | Pass/Fail/Blocked/Not run | <published video or reason absent> |

Preserve the regression-scope IDs, titles, and order. Account for every UI
workflow exactly once. State when no material UI workflow was found.

## Automated checks

| Check | Implementation result | CI status |
|---|---|---|
| <unit/integration/type/lint/build check> | Pass/Fail/Not run | Pending |

These results come from the implementation packet; verification did not rerun
them.

## Review and confidence

- **Review:** <verdict and unresolved findings>
- **Verification verdict:** <pass/fail/inconclusive/blocked>
- **Regression statement:** <no regressions observed in the verified scope, or failures>
- **Evidence gaps:** <missing or stale evidence>
- **Residual risk:** <remaining unknowns>
- **Human decision:** <approval, exception, or more work>
