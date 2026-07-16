# PR Verification Report

## Summary

- **Why:** <intended outcome>
- **Changed:** <implemented behavior>
- **Affected:** <users, systems, contracts, data, and operations>

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| <criterion> | Pass/Fail/Unverified | <implementation and observed proof> |

## Manual regression tests

| ID | Surface | Test case | Result | Evidence |
|---|---|---|---|---|
| <scope ID> | <UI/API/CLI/worker/other> | <scope title> | Pass/Fail/Blocked/Not run | <observed result and artifact> |

Preserve the regression-scope IDs, titles, and order. Account for every manual
test case exactly once. Include visual comparisons when applicable and state
when no material manual test case was found.

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
