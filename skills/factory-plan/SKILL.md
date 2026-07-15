---
name: factory-plan
description: "Use only when the human explicitly starts the planning lifecycle and supplies context for a change. Convert all supplied context into a detailed, implementation-ready plan for an implementor agent without editing files or implementing the change."
---

# Factory Plan

Convert the supplied context into the smallest complete implementation plan.

## Workflow

1. Read all supplied context and applicable repository instructions.
2. Inspect the repository only as needed to ground the plan in current code.
3. Resolve the requested behavior into ordered, concrete implementation steps.
4. Include targeted tests and verification for every behavior change.
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
- unit, integration, and manual verification steps with expected outcomes
- assumptions, risks, dependencies, blockers, and rollback notes where relevant

If the context is contradictory or lacks a decision that materially changes the
implementation, return the specific blocker instead of inventing requirements.

Stop after returning the plan or blocker.
