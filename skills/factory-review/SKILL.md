---
name: factory-review
description: "Perform one bounded, read-only review of a supplied subject and return one structured result. The primary orchestrator owns reviewer count, model tier, isolation, and dispatch."
---

# Factory Review

Perform 1 independent, read-only review.

When orchestrated, the primary thread must delegate this skill to the routed
tier worker. That worker must not spawn another lifecycle actor.

The caller supplies the focus, tier, and bounded assignment. Do not spawn
agents, invoke another CLI, select a model, coordinate reviewers, or merge
results.

## Review

Read the complete subject, context, criteria, repository or worktree, and
instructions. Without a supplied focus, assess relevant correctness,
completeness, consistency, feasibility, risk, and regressions.

Report every supported finding with severity, exact location, evidence, impact,
smallest safe recommendation, and confidence.

For implementation review, reconcile the whole base-to-head diff with the
canonical assurance report. Confirm every diff region belongs to a coherent
change group; every group maps to a behavioral path or justified non-behavioral
class; boundary evidence reaches that path; and assertions prove the claimed
outcome. Treat omissions, implicit paths, unsupported inspection claims, and
overstated evidence as blocking completeness findings.

Return `incomplete` when required context is unavailable. Do not retry,
substitute a model, inspect another reviewer's result, or start another
lifecycle. Review only the supplied revision unless history is an explicit
criterion.

## Output

Return an agent result with:

- scope and criteria
- verdict: `approve`, `approve-with-findings`, `reject`, or `incomplete`
- numbered findings with severity, location, evidence, impact, recommendation,
  and confidence
- questions, evidence gaps, and residual risk

When orchestrated, also write one human `report.md` with numbered, descriptive
findings, concrete locations, impact, and the smallest safe recommendation.
Keep stable IDs and wide mappings in the agent result.

If there are no findings, state what was inspected and what remains uncertain.
Do not fix findings.
