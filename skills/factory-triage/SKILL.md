---
name: factory-triage
description: "Research, bound, classify, and prepare a Factory software change for implementation. Use after intake for bug fixes, features, refactors, configuration, migrations, and documentation changes."
---

# Factory Triage

Produce one implementation-ready change packet with proportional proof.

## Inputs

Require an aligned task contract, repository, supplied evidence, permitted
sources, and current task revision.

## Operation

1. Inspect the smallest relevant code, tests, configuration, documentation,
   history, and authoritative external sources.
2. Separate confirmed facts, supported inferences, conflicts, and unknowns.
3. Establish the current baseline. For a bug, select permanent red-green proof
   when it can reproduce the reported behavior. Require separate reproduction
   only for intermittent, environment-specific, unclear, or unsafe failures.
4. Trace each affected behavior through callers, data, permissions, side
   effects, integrations, consumers, and observable outcomes. For migrations
   and destructive operations, inspect source and destination validation,
   intermediate states, interruption boundaries, and recovery. Map these risks
   to proof within this triage; do not add a stage.
5. Define the smallest implementation steps. Map each acceptance criterion,
   behavioral path, and material risk to the cheapest sufficient proof.
6. Classify impact, uncertainty, reasoning difficulty, proof difficulty, and
   input gaps as low, medium, or high.
7. Evaluate every low-risk condition. Mark the task eligible only when all are
   true and known:
   - clear requirements and acceptance criteria
   - clean worktree
   - localized and reversible change
   - established local pattern or exact precedent
   - deterministic focused proof
   - low impact, uncertainty, reasoning, and proof difficulty
   - no input gap
   - no security policy, authorization rule, sensitive data, schema, migration,
     concurrency, infrastructure, public contract, or irreversible effect
8. Require independent plan assurance when any signal is high or when the
   change affects a listed sensitive surface. Use it for medium risk when a
   material design choice remains.

Do not add diagrams, code previews, or separate artifacts unless they make a
material decision easier to verify.

## Outputs

Return:

- status: `ready`, `needs-input`, or `blocked`
- current assurance record containing the affected behavior, implementation
  steps, proof mappings, risk assessment, and plan-assurance decision
- a short summary of material assumptions, blockers, and required decisions

## Side effects

Read local and permitted authoritative sources. Do not run mutating checks,
approve the plan, or change repository or external-system state.

## Failure results

Return `needs-input` for a material human decision. Return `blocked` for missing,
stale, contradictory, or inaccessible required evidence.
