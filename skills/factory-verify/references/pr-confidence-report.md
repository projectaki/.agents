# PR Verification Report

## Summary

- **Why:** <intended outcome>
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

## Scope reconciliation

- **Planned risks retained:** <risk IDs>
- **New final-diff risks:** <risk IDs>
- **Planned risks removed:** <risk IDs and reason>

## Review and confidence

- **Review:** <verdict and unresolved findings>
- **Verification verdict:** <pass/fail/inconclusive/blocked>
- **Regression statement:** <no regressions observed in the verified scope, or failures>
- **Evidence gaps:** <missing or stale evidence>
- **Residual risk:** <remaining unknowns>
- **Next work:** <specific tests, evidence, or implementation changes>
- **Human decision:** <approval, exception, or more work>
