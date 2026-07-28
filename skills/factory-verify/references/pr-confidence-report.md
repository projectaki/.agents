# PR Verification Report

## Summary

- **Outcome:** <current intended behavior>
- **Changed:** <implemented behavior>
- **Affected:** <users, systems, contracts, data, and operations>
- **Change set:** <base, head, and diff fingerprint>

## Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| <criterion> | Pass/Fail/Unverified | <current implementation and observed proof> |

## Regression risk coverage

| Risk ID | Affected behavior | Evidence | Result | Remaining gap |
|---|---|---|---|---|
| <risk ID> | <behavior and failure mode> | <test or observation> | Pass/Fail/Unverified | <next evidence or none> |

Preserve regression-scope IDs and account for every material risk exactly once.

## Automated checks

| Check | Source | Covered head | Result | CI status |
|---|---|---|---|---|
| <targeted check> | Implementation/Verification | <commit or diff> | Pass/Fail/Not run | Pending |

State exactly which checks verification ran. Prefer targeted fast checks; leave
remote CI pending.

## Manual and video evidence

| Risk ID | Evidence | Why automation was insufficient | Result | Artifact |
|---|---|---|---|---|
| <risk ID> | Manual/Video | <justification> | Pass/Fail/Blocked/Not run | <artifact or reason absent> |

State when no manual or video evidence was required. A missing video is not a
gap when automated evidence sufficiently covers the risk.

## Review and confidence

- **Review:** <verdict and unresolved findings>
- **Verification verdict:** <pass/fail/inconclusive/blocked>
- **Regression statement:** <no regressions observed in the verified scope, or failures>
- **Evidence gaps:** <missing or stale evidence>
- **Residual risk:** <remaining unknowns>
- **Next work:** <specific tests, evidence, or implementation changes>
- **Human decision:** <approval, exception, or more work>

Describe only the current verified change set. Do not include revision history,
removed risks, earlier failures, corrected mistakes, or superseded scope.
