# PR Verification Report

## Readiness

<Pass, fail, blocked, or more evidence needed, followed by the concrete reason.>

- **Intended outcome:** <current intended behavior>
- **Implemented:** <implemented behavior>
- **Affected:** <users, systems, contracts, data, and operations>
- **Verified revision:** <short commit reference when useful>

Lead with failures, unverified behavior, and accepted exceptions.

## Verified behavior

Use one block for each distinct changed behavior. Do not combine several
endpoints, routes, jobs, or consumers into a count-based item.

### <Plain behavior name>

- **Expected:** <observable claim>
- **Affected boundary:** <caller, API, component, or user boundary>
- **Result:** <Pass, fail, unverified, or exception accepted>
- **Evidence:** <descriptive links to final code and inspection, or exact test
  code and matching result>
- **Remaining risk:** <risk or none>

Repeat this block for every changed behavior. Keep internal path and evidence
IDs in the agent packet.

## Acceptance criteria

Use a short bullet for each criterion:

- **<Criterion in plain language> — <Pass, fail, or unverified>.** <Evidence or
  remaining gap.>

## Regression risks

Use one block per material risk.

### <Plain risk name>

- **Could affect:** <behavior and failure mode>
- **Result:** <Pass, fail, or unverified>
- **Evidence:** <test, inspection, or observation>
- **Remaining gap:** <next evidence or none>

## Checks run

List each check with its result and scope. State which checks verification ran
and which were supplied by implementation. Leave remote CI marked as pending.

- **<Check name> — <Pass, fail, or not run>.** <Covered behavior and revision.>

## Visual evidence

Include this section only when a screenshot or video was required because
automation could not prove the observable property.

### <Plain behavior name>

- **Evidence:** <Screenshot or video>
- **Why automation was insufficient:** <concrete reason>
- **Result:** <Pass, fail, blocked, or not run>
- **Artifact:** <reviewer-accessible link or reason absent>

## Review and confidence

- **Review:** <verdict and unresolved findings>
- **Verification verdict:** <pass/fail/inconclusive/blocked>
- **Regression statement:** <no regressions observed in the verified scope, or failures>
- **Evidence gaps:** <missing or stale evidence>
- **Residual risk:** <remaining unknowns>
- **Next work:** <specific tests, evidence, or implementation changes>
- **Human decision:** <approval, exception, or more work>

Describe only the current verified change set. Do not include revision history,
removed risks, earlier failures, corrected mistakes, or superseded scope. Do
not include internal path, risk, change-group, or evidence IDs.
