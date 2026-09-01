---
name: factory-triage
description: "Research, bound, classify, and prepare a Factory software change for implementation. Use after intake for bug fixes, features, refactors, configuration, migrations, and documentation changes."
---

# Factory Triage

## Purpose

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
   effects, integrations, consumers, and observable outcomes.
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
- current behavior, relevant precedent, affected surfaces, and consumers
- ordered implementation steps with expected files and symbols
- behavioral paths, observable outcomes, risks, and failure modes
- tests and evidence mapped to every acceptance criterion and material risk
- low-risk gate with every condition and its evidence
- explicit sensitive-change result
- risk signals and required worker tier
- whether plan assurance is required and why
- assumptions, exclusions, unknowns, blockers, and exact human decisions
- complete current assurance record

## Side effects

Read local and permitted authoritative sources. Make no repository or external
system changes.

## Failure results

Return `needs-input` for a material human decision. Return `blocked` for missing,
stale, contradictory, or inaccessible required evidence.

## Non-goals

Do not edit files, run mutating checks, approve the plan, implement, commit, or
publish.
