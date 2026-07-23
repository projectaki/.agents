---
name: factory-regression-scope
description: "Use when the human explicitly starts post-implementation regression scoping for a completed change before factory-verify. Inspect the exact final change set, trace affected behavior, and produce a prioritized regression-risk and evidence-gap packet without running checks."
---

# Factory Regression Scope

Determine what the completed implementation could have regressed. Remain
read-only.

## Input

Require the exact base, head, and complete diff. Read the task, acceptance
criteria, approved plan, implementation packet, repository instructions,
relevant tests, and pre-development test-scope packet when supplied. If the
change set is incomplete or ambiguous, return the precise blocker.

## Workflow

1. Inventory every changed file, symbol, behavior, configuration, schema, flag,
   and shared dependency.
2. Trace callers, consumers, routes, endpoints, jobs, state, permissions, data
   boundaries, and user-visible behavior beyond the edited files.
3. Derive direct and plausible adjacent regression risks. Preserve matching
   pre-development risk IDs and assign stable IDs to newly discovered risks.
4. Map each risk to current-head evidence. Classify evidence as sufficient,
   missing, stale, failed, or inaccessible.
5. Recommend the cheapest reliable next evidence for every gap, in this order:
   unit, integration, contract, component, deterministic end-to-end, manual
   observation, then video.
6. Recommend video only when a reviewer must assess a visual or transient
   property that deterministic assertions or recorded results cannot prove.
   Include the reason automation is insufficient and a complete, shortest-path
   UI workflow for each video-required risk.

## Output

Return one regression-scope packet containing:

- exact base, head, diff fingerprint, change summary, and assumptions
- changed files and symbols mapped to affected behavior and consumers
- ordered risk register with ID, source (`planned` or `new`), priority, failure
  mode, impact, and affected surfaces
- current evidence and status mapped to every risk ID
- smallest recommended next evidence for each gap, including candidate test
  target or command when known
- differences from the pre-development test scope
- complete workflows only for risks marked `video-required`, including
  rationale, preconditions, environment, fixtures, actions, expected result,
  cleanup, and approval prerequisites
- intentionally excluded areas, unknowns, and blockers

Do not execute checks or workflows, modify files, create evidence, or treat the
absence of a video as a gap when automated evidence is sufficient.
