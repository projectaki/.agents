---
name: factory-plan
description: "Use only when the human explicitly starts the planning lifecycle with change context and a completed factory-test-scope packet. Convert those inputs into a detailed, implementation-ready plan without editing files or implementing the change."
---

# Factory Plan

Convert the supplied context into the smallest complete implementation plan.

## Input

Require a current `$factory-test-scope` packet for the proposed change. If it is
missing, stale, or based on materially different acceptance criteria, return
the precise blocker.

## Workflow

1. Read all supplied context and applicable repository instructions.
2. Inspect the repository only as needed to ground the plan in current code.
3. Resolve the requested behavior into ordered, concrete implementation steps.
4. Map every test-scope risk ID to targeted test work or an explicit evidence
   exception.
5. Record relevant assumptions, risks, dependencies, and blockers.

Do not edit files or implement the change. Do not add speculative refactors or
requirements not supported by the context.

## Output

Return one self-contained plan that an implementor agent can execute without
reconstructing the analysis. Include:

- objective, scope, and acceptance criteria
- current behavior and relevant architecture
- ordered steps with expected files, symbols, and logic changes
- error handling, edge cases, migrations, and observability where relevant
- test-scope risk IDs mapped to unit, integration, contract, component, or
  end-to-end test work and expected outcomes
- explicitly justified non-automated evidence exceptions
- assumptions, risks, dependencies, blockers, and rollback notes where relevant

If the context is contradictory or lacks a decision that materially changes the
implementation, return the specific blocker instead of inventing requirements.

Stop after returning the plan or blocker.
