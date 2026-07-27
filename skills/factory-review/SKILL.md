---
name: factory-review
description: "Perform one bounded, read-only review of a supplied subject and return one structured review result. Reviewer count, model tier, isolation, and dispatch are owned by the primary orchestrator."
---

# Factory Review

Perform one independent, read-only review of the supplied subject.

The caller supplies the reviewer focus, selected model tier, and bounded assignment. Do not spawn agents, invoke another CLI, choose a model, coordinate other reviewers, or merge other review results.

## Input

Read the complete subject, context, focus, criteria, repository or worktree, and applicable instructions. If no focus is supplied, assess relevant correctness, completeness, consistency, feasibility, risk, and regression concerns.

## Review

Inspect the complete supplied subject against the supplied criteria. Report all supported findings in one result. Each finding must include severity, precise subject location, evidence, impact, the smallest safe recommendation, and confidence.

Do not modify the subject or inspect another reviewer's result. If required context is missing or unavailable, return `incomplete`; do not retry, substitute a model, or start another lifecycle.

## Output

Return:

- reviewed scope and criteria
- verdict: `approve`, `approve-with-findings`, `reject`, or `incomplete`
- numbered findings with severity, location, evidence, impact, recommendation, and confidence
- questions, evidence gaps, and residual risk

A no-findings result must state what was inspected and what remains uncertain. Do not fix findings or start another lifecycle.
