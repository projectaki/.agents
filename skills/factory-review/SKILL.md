---
name: factory-review
description: "Perform one bounded, read-only review of a supplied subject and return one structured review result. Reviewer count, model tier, isolation, and dispatch are owned by the primary orchestrator."
---

# Factory Review

## Execution boundary

When used by the orchestrator, the primary thread must spawn the tier worker
selected by routing and instruct that worker to use this skill. The primary
thread must not perform this lifecycle workflow. A tier worker executes the
workflow directly and does not spawn another lifecycle actor.

Perform one independent, read-only review of the supplied subject.

The caller supplies the reviewer focus, selected model tier, and bounded assignment. Do not spawn agents, invoke another CLI, choose a model, coordinate other reviewers, or merge other review results.

## Input

Read the complete subject, context, focus, criteria, repository or worktree, and applicable instructions. If no focus is supplied, assess relevant correctness, completeness, consistency, feasibility, risk, and regression concerns.

## Review

Inspect the complete supplied subject against the supplied criteria. Report all supported findings in one result. Each finding must include severity, precise subject location, evidence, impact, the smallest safe recommendation, and confidence.

For an implementation review, reconcile the entire base-to-head diff against
the canonical change-assurance report. Confirm that every diff region belongs
to a coherent change group, every group maps to a behavioral path or justified
non-behavioral classification, boundary-level evidence actually reaches the
path, and its assertions prove the claimed outcomes. Treat an omitted change,
implicit path, unsupported inspection claim, or overstated evidence scope as a
blocking completeness finding.

Do not modify the subject or inspect another reviewer's result. If required context is missing or unavailable, return `incomplete`; do not retry, substitute a model, or start another lifecycle.

Review and describe only the supplied revision. Context may establish expected
behavior but is not review content. Do not discuss findings from earlier
revisions, already-corrected mistakes, or how the subject changed unless the
review criteria explicitly require historical analysis.

## Output

Return the agent-oriented review result with:

- reviewed scope and criteria
- verdict: `approve`, `approve-with-findings`, `reject`, or `incomplete`
- numbered findings with severity, location, evidence, impact, recommendation, and confidence
- questions, evidence gaps, and residual risk

When used by the orchestrator, also provide the lifecycle's single human
`report.md`. Use numbered findings with descriptive titles, concrete locations,
impact, and the smallest safe recommendation. Do not make the reader decode
stable IDs or wide traceability tables.

A no-findings result must state what was inspected and what remains uncertain. Do not fix findings or start another lifecycle.
