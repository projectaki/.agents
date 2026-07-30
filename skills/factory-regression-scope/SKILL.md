---
name: factory-regression-scope
description: "Use when the human explicitly starts post-implementation regression scoping before factory-verify. Account for the exact final diff, trace grouped behavioral paths, and return change assurance, current risks, and evidence gaps without running checks."
---

# Factory Regression Scope

Find what the completed implementation could regress. Remain read-only.

When orchestrated, the primary thread must delegate this skill to the routed
tier worker. That worker must not spawn another lifecycle actor.

## Input

Require exact base, head, and complete diff. Read the task, criteria, approved
plan, implementation packet, repository instructions, relevant tests, and
pre-development scope when supplied. Return the exact blocker for an incomplete
or ambiguous change set.

## Workflow

1. Inventory every changed file, symbol, behavior, configuration, schema, flag,
   and shared dependency.
2. Group the whole diff. Map every group to a behavioral path or precise
   non-behavioral class. Trace paths up to the highest reliable observable
   boundary and down through callers, consumers, routes, endpoints, jobs,
   state, permissions, data, and user effects.
3. Derive direct and plausible adjacent risks. Reuse applicable earlier risk
   IDs; assign stable IDs to the rest.
4. Map each risk to current-head evidence classified as `sufficient`,
   `missing`, `stale`, `failed`, or `inaccessible`.
5. For each gap, recommend the cheapest sufficient next proof: corroborated
   inspection for simple non-behavioral or behavior-preserving changes;
   otherwise focused unit, integration, contract, component, or deterministic
   end-to-end automation; then visual evidence only when automation cannot
   prove the property.
6. Use screenshots only for static visual properties. Use video only for a
   sequence, gesture, animation, timing, or transition that deterministic
   assertions cannot prove. Explain why and provide the complete shortest
   workflow.

## Output

Return an agent packet with:

- base, head, diff fingerprint, summary, and assumptions
- current assurance report mapping the complete diff to paths, observable
  boundaries, consumers, and evidence
- ordered risks with ID, priority, failure mode, impact, and surfaces
- evidence status and smallest next proof for every risk, including likely
  target or command
- complete workflows only for `video-required` risks: rationale, preconditions,
  environment, fixtures, actions, result, cleanup, and approval needs
- capture requirements for `screenshot-required` risks
- exclusions, unknowns, and blockers

When orchestrated, also write one human `report.md` naming each behavior and
material risk, its proof or gap, and the consequence. Keep IDs and full mappings
in the agent packet.

Describe only the exact final change set. Preserve earlier IDs without their
history. Do not run checks or workflows, edit files, create evidence, or require
video when automation is sufficient.
