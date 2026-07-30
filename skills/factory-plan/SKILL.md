---
name: factory-plan
description: "Use only when the human explicitly starts planning with a current factory-analysis packet. Produce an implementation-ready plan without editing files or implementing."
---

# Factory Plan

Create the smallest complete implementation plan.

When orchestrated, the primary thread must delegate this skill to the routed
tier worker. That worker must not spawn another lifecycle actor.

## Inputs

Require a current `factory-analysis` packet for the proposed change. Return
the exact blocker if it is missing, stale, or based on materially different
acceptance criteria.

## Workflow

1. Read supplied context and repository instructions.
2. Inspect only enough current code to ground the plan.
3. Define ordered, concrete implementation steps.
4. Map every behavioral path and analysis risk ID to corroborated inspection,
   targeted automation, visual evidence only when automation is insufficient,
   or a human-approved evidence exception.
5. Record assumptions, risks, dependencies, and blockers.

Do not edit, implement, add unsupported requirements, or plan speculative
refactors. Describe current requirements and constraints without revision
history or discarded approaches.

## Output

Return a self-contained agent plan with:

- objective, scope, and acceptance criteria
- current behavior and relevant architecture
- ordered steps with expected files, symbols, and logic
- relevant errors, edge cases, migrations, observability, and rollback
- risk IDs mapped to test level, work, and expected result
- path IDs mapped to implementation steps and cheapest sufficient proof
- justified non-automated exceptions
- assumptions, risks, dependencies, blockers, and required decisions

When orchestrated, also write one human `report.md` for approval. Use plain
behavior and risk names, ordered steps, and small sections. Keep IDs and full
mappings in the agent plan; avoid tables wider than 4 columns.

Return a specific blocker instead of inventing a material decision. Stop after
the plan or blocker.
