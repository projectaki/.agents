---
name: factory-regression-scope
description: "Use when the human explicitly starts post-implementation regression scoping for a completed change before factory-verify. Account for the exact final diff, trace grouped behavioral paths, and produce the change-assurance, regression-risk, and evidence-gap packet without running checks."
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
2. Reconcile the complete diff into stable change groups. Map every group to a
   behavioral path or a precise non-behavioral classification. Trace each path
   upward to its highest reliable observable boundary and downward through
   callers, consumers, routes, endpoints, jobs, state, permissions, data
   boundaries, and user-visible effects.
3. Derive direct and plausible adjacent regression risks. Reuse applicable
   pre-development risk IDs and assign stable IDs to all other current risks.
4. Map each risk to current-head evidence. Classify evidence as sufficient,
   missing, stale, failed, or inaccessible.
5. Recommend the cheapest sufficient next evidence for every gap: corroborated
   inspection for simple non-behavioral or behavior-preserving changes;
   otherwise focused unit, integration, contract, component, or deterministic
   end-to-end automation; then screenshot or video only when automation cannot
   prove the relevant property.
6. Recommend a screenshot only for a static visual property, or video when a
   reviewer must assess a sequence, gesture, animation, timing, or state
   transition that deterministic assertions cannot prove. Include the reason
   automation is insufficient and a complete, shortest-path UI workflow for
   each video-required risk.

## Output

Return one agent-oriented regression-scope packet containing:

- exact base, head, diff fingerprint, change summary, and assumptions
- a change-assurance report following the orchestrator contract, with the
  complete diff grouped and mapped to behavioral paths, observable boundaries,
  affected consumers, and current evidence
- ordered current risk register with ID, priority, failure mode, impact, and
  affected surfaces
- current evidence and status mapped to every risk ID
- smallest recommended next evidence for each gap, including candidate test
  target or command when known
- complete workflows only for risks marked `video-required`, including
  rationale, preconditions, environment, fixtures, actions, expected result,
  cleanup, and approval prerequisites
- static capture requirements for risks marked `screenshot-required`
- intentionally excluded areas, unknowns, and blockers

When used by the orchestrator, also provide the lifecycle's single human
`report.md`. Name every affected behavior and material risk directly. State
what has proof, what still needs proof, and the consequence of each gap. Keep
stable IDs and exhaustive many-to-many mappings in the internal packet.

Return a snapshot of risk for the exact final change set. Do not narrate how the
scope evolved, label risks as old or new, list removed risks, or explain why an
earlier packet was incomplete. Preserve prior IDs only as stable identifiers.

Do not execute checks or workflows, modify files, create evidence, or treat the
absence of a video as a gap when automated evidence is sufficient.
