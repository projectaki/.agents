---
name: factory-review
description: "Perform one bounded, independent, read-only review of a supplied subject. Apply the supplied focus and criteria, report supported findings and evidence gaps, and do not fix the subject."
---

# Factory Review

## Purpose

Perform one independent and read-only review.

## Inputs

Require a bounded subject, review focus, criteria, relevant context, repository
or worktree when applicable, and supporting evidence. Without a supplied focus,
assess relevant correctness, completeness, consistency, feasibility, risk, and
regressions.

The caller owns reviewer count, worker selection, isolation, and result
aggregation. Review only the supplied revision unless history is an explicit
criterion.

## Operation

1. Read the complete subject, context, criteria, evidence, and repository
   instructions.
2. Report each supported finding with severity, exact location, evidence,
   impact, smallest safe recommendation, and confidence.
3. For a code-change review, reconcile the complete base-to-head diff with the
   supplied change-assurance record.
4. Trace each change group through callers, consumers, data, permissions, side
   effects, and observable behavior.
5. Identify direct and adjacent regression risks. Map each risk to current
   evidence as `sufficient`, `missing`, `stale`, `failed`, or `inaccessible`.
6. Require the cheapest sufficient proof. Recommend visual evidence only when
   automation cannot prove the property.
7. Reconcile the supplied acceptance-proof record with the task contract,
   impact analysis, plan, diff, and change-assurance record.

Treat unaccounted diff regions, implicit paths, unsupported claims, missing
material evidence, overstated evidence, open universal inventories, proof
substitution without an accepted exception, overbroad waivers, duplicate
mappings, and evidence for a different revision as blocking findings.

## Outputs

Return a structured result and a concise human summary with:

- scope and criteria
- verdict: `approve`, `approve-with-findings`, `reject`, or `incomplete`
- numbered findings with severity, location, evidence, impact, recommendation,
  and confidence
- questions, evidence gaps, and residual risk
- for a code-change review, complete diff accountability, regression risks,
  evidence status, and the smallest next proof for each gap

Keep stable identifiers and wide mappings in the structured result. Use
descriptive finding names in the human summary. If there are no findings, state
what was inspected and what remains uncertain.

## Side effects

Read supplied sources and run permitted non-mutating inspection commands. Make
no persistent repository or external-system changes.

## Failure results

Return `incomplete` when required context or evidence is unavailable. Do not
retry with a different worker or inspect another reviewer's result.

## Non-goals

Do not coordinate reviewers, select workers, merge results, or fix findings.
