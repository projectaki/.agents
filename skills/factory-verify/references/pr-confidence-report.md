# PR Verification Report

## Summary

- **Outcome:** <current intended behavior>
- **Changed:** <implemented behavior>
- **Affected:** <users, systems, contracts, data, and operations>
- **Change set:** <base, head, and diff fingerprint>

## Change-path assurance

<!-- Lead with failures, unverified paths, or exceptions. Group large diffs by
behavioral path; do not create one row per file or hunk. -->

| Path | Behavioral claim | Change category | Highest reliable boundary | Evidence | Result | Residual risk |
|---|---|---|---|---|---|---|
| <P#> | <observable behavior> | <category and risk> | <caller, API, component, or user boundary> | <durable E# links> | Pass/Fail/Unverified/Exception accepted | <risk or none> |

Account for every final-diff change group through these paths or a justified
non-behavioral classification. Link to final code for inspection evidence, to
test code plus its matching result for automated evidence, and to a
reviewer-accessible artifact for screenshot or video evidence.

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

## Screenshot and video evidence

| Path and risk IDs | Evidence | Why automation was insufficient | Result | Artifact |
|---|---|---|---|---|
| <P# and R#> | Screenshot/Video | <justification> | Pass/Fail/Blocked/Not run | <reviewer-accessible link or reason absent> |

State when no screenshot or video evidence was required. Missing visual
evidence is not a gap when automation sufficiently covers the risk.

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
