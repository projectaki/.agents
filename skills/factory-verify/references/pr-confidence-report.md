# PR Verification Report

## Summary

- **Why:** <intended outcome>
- **Changed:** <implemented behavior>
- **Affected:** <users, systems, contracts, data, and operations>

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| <criterion> | Pass/Fail/Unverified | <implementation and observed proof> |

## Regression evidence

| ID | Surface | Scenario | Result | Evidence |
|---|---|---|---|---|
| <scope ID> | <UI/API/CLI/worker/other> | <flow or command> | Pass/Fail/Blocked/Not run | <artifact or observation> |

Account for every regression-scope scenario. Include visual comparisons when
applicable and state when no material manual scenario was found.

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
