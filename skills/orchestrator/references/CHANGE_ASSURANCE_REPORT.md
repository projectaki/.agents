# Internal Change Assurance Contract

The canonical agent-oriented record for final-diff accountability is:

```text
<branch-task-root>/change-assurance-report.md
```

Create it during `IMPLEMENTATION`, reconcile it against the exact completed
diff during regression scoping and review, finalize its evidence during
`VERIFICATION`, and use it to derive the human lifecycle reports and PR
description.

This is not a human lifecycle report. Stable IDs, wide traceability matrices,
diff fingerprints, and exhaustive evidence mappings belong here. Every
lifecycle still writes one separate `report.md` following
`HUMAN_REPORTS.md`. Translate internal IDs into plain behavior, risk, and check
names in that report.

The report answers two different questions:

1. Has every part of the final diff been accounted for?
2. Is every changed behavioral path supported by sufficient current evidence?

Do not require one test or report row per file, hunk, or internal function.
Group related edits into meaningful behavioral paths and verify them at the
highest reliable observable boundary.

## Stable IDs

Reuse the analysis report's `P#` behavioral-path IDs. Add stable identifiers:

| Prefix | Meaning |
| --- | --- |
| `G#` | Change group containing related final-diff regions |
| `E#` | Evidence item supporting one or more paths |

Preserve IDs across revisions when their meaning remains the same. Retire
obsolete entries explicitly rather than silently reusing their IDs.

## Completeness invariants

- Record the exact base, head, and diff fingerprint.
- Account for the complete base-to-head diff. Every changed region belongs to
  a `G#` group and maps to one or more `P#` paths, or has a precise
  non-behavioral classification.
- Use locators precise enough to recover the covered diff without creating one
  row per hunk. A group may include several files or regions only when they
  serve the same behavioral claim.
- Trace each `P#` from its trigger or highest relevant caller through changed
  surfaces to its observable result and material consumers or side effects.
- Allow one boundary-level check to cover many change groups or paths only when
  the report explains reachability and identifies the assertions that prove
  their relevant outcomes.
- Give every `P#` a final verdict and one or more `E#` items. No path may be
  implicitly covered by a broad suite name, reviewer confidence, or another
  path's evidence.
- Bind evidence to the final revision. Stale evidence is unverified.
- Block delivery for failed, missing, inaccessible, or pending evidence unless
  the human explicitly accepts the documented exception and residual risk.
- Keep the overview readable regardless of diff size. Put exhaustive diff
  locators in the accountability section, not in the opening summary.

## Evidence selection

Choose the cheapest evidence that is sufficient for the claim:

1. **Corroborated inspection** — Use a one-sentence reason for a simple
   non-behavioral or behavior-preserving change. Add a typecheck, compilation,
   static analysis, reference search, generated-file check, or equivalent
   corroborating signal whenever one is available. If none exists, say why the
   inspection is sufficient.
2. **Automated behavioral evidence** — Use a focused unit, integration,
   contract, component, or end-to-end check. Select the highest reliable
   observable boundary that proves the path without choosing a broader, slower
   boundary than necessary.
3. **Visual or interaction evidence** — Use a screenshot for a static visual
   property and a video for a sequence, gesture, animation, timing, or state
   transition only when deterministic automation cannot sufficiently prove the
   property.
4. **Human-accepted exception** — State why verification is unavailable, the
   affected paths, the residual risk, the approver, and the approval reference.
   An unaccepted exception is blocking.

Durable evidence references are:

- a concise inspection statement plus links to relevant final code and any
  corroborating result;
- an immutable test-code permalink plus the matching execution result or CI
  run;
- a reviewer-accessible screenshot or video URL;
- an explicit human-approval reference for an exception.

Local paths, inferred test coverage, a test name without inspected assertions,
and an execution result without identifiable scope are not durable PR evidence.

## Required internal structure

### 1. Assurance state

State the intended outcome, system reach, dominant regression concern, base,
head, and diff fingerprint. Include counts for:

- changed files and `G#` groups;
- `P#` paths by change category and risk;
- paths proven by inspection, automation, visual evidence, or exception;
- passed, failed, unverified, and exception-pending paths.

Put failures, unverified paths, and exceptions before passing detail.

### 2. Behavioral traceability map

Record the changed flow at meaningful boundaries. This internal map may use
stable IDs. A human report must redraw or restate any useful part with plain
names and the diagram rules in `HUMAN_REPORTS.md`.

### 3. Path assurance matrix

| Path | Behavioral claim | Category and risk | Highest reliable boundary | Change groups | Evidence | Verdict | Residual risk |
| --- | --- | --- | --- | --- | --- | --- | --- |

Use verdicts `pass`, `fail`, `unverified`, `exception-pending`, or
`exception-accepted`.

### 4. Diff accountability

| Group | Final-diff locators | Change summary | Paths or non-behavioral classification | Accountability rationale |
| --- | --- | --- | --- | --- |

The listed locators must collectively account for the complete diff. Include
code, tests, configuration, schemas, generated files, documentation, and
deletions. Summarize large mechanical groups, but retain precise locators.

### 5. Evidence index

| Evidence | Type | Proves | Final-revision reference | Result |
| --- | --- | --- | --- | --- |

For automated evidence, link both the test code and its result. For inspection,
include the short reasoning and corroborating signal. For screenshots or video,
state why automation was insufficient.

### 6. Exceptions and residual risk

List every accepted or pending exception, approval state, and residual risk.
State `none` when there are no exceptions.

## Lifecycle responsibilities

- `ANALYSIS`: establish expected `P#` paths and planned proof.
- `PLANNING`: map implementation and evidence work to every `P#`.
- `IMPLEMENTATION`: create the report, map the working diff into `G#` groups,
  and record evidence already produced.
- `REVIEW`: independently reconcile the entire diff, path map, claims, and
  evidence scope. Missing groups or paths are blocking findings.
- `VERIFICATION`: bind the report to the final revision, execute or inspect the
  required evidence, and assign every path a verdict.
- `DELIVERY`: put the assurance summary and path matrix in the PR description
  using plain behavior and risk names with durable evidence links. Put
  exhaustive accountability detail in a collapsed section only when reviewers
  genuinely need it, or use a durable reviewer-accessible link when one already
  exists. Never link a local lifecycle artifact or expose an ID-only matrix as
  reviewer-facing content.
