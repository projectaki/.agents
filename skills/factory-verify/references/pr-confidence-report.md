# PR Verification Report

## Readiness

<Pass, fail, blocked, or more evidence needed, with reason.>

- **Intended outcome:** <behavior>
- **Implemented:** <behavior>
- **Affected:** <users, systems, contracts, data, and operations>
- **Verified revision:** <short commit when useful>

Lead with failures, unverified behavior, and accepted exceptions.

## Verified behavior

<!-- Repeat per distinct behavior. Do not combine consumers or expose IDs. -->

### <Behavior>

- **Expected:** <observable claim>
- **Affected boundary:** <caller, API, component, or user boundary>
- **Result:** <Pass, fail, unverified, or exception accepted>
- **Evidence:** <final code and inspection, or exact test code and result>
- **Remaining risk:** <risk or none>

## Acceptance criteria

- **<Criterion> — <Pass, fail, or unverified>.** <Evidence or gap.>

## Regression risks

<!-- Repeat per material risk. -->

### <Risk>

- **Could affect:** <behavior and failure mode>
- **Result:** <Pass, fail, or unverified>
- **Evidence:** <test, inspection, or observation>
- **Remaining gap:** <next proof or none>

## Checks run

<!-- Name result, scope, source, and revision. Mark remote CI pending. -->

- **<Check> — <Pass, fail, or not run>.** <Scope and source.>

## Visual evidence

<!-- Include only when automation could not prove a required property. -->

### <Behavior>

- **Evidence:** <Screenshot or video>
- **Why automation was insufficient:** <reason>
- **Result:** <Pass, fail, blocked, or not run>
- **Artifact:** <reviewer-accessible link or reason absent>

## Review and confidence

- **Review:** <verdict and open findings>
- **Verification verdict:** <pass/fail/inconclusive/blocked>
- **Regression statement:** <no regressions observed in scope, or failures>
- **Evidence gaps:** <missing or stale evidence>
- **Residual risk:** <unknowns>
- **Next work:** <specific work>
- **Human decision:** <approval, exception, or more work>

Describe only the current verified change. Omit revision history, removed risks,
earlier failures, corrected mistakes, superseded scope, and internal IDs.
