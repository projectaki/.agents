---
name: factory-test-scope
description: "Use when the human explicitly starts pre-development test scoping for a proposed change before factory-plan. Trace the intended behavior through the existing codebase and produce a prioritized automated-test scope without editing files or running tests."
---

# Factory Test Scope

Define the smallest reliable test coverage for a proposed change before
implementation. Remain read-only.

## Input

Read the requested behavior, acceptance criteria, context, repository
instructions, relevant architecture, and existing tests. If the intended
behavior is materially undecided, return the precise blocker.

## Workflow

1. Trace the intended behavior through domain logic, APIs, data, permissions,
   jobs, configuration, shared consumers, and UI boundaries.
2. Identify direct and plausible adjacent regression risks. Assign each a
   stable risk ID, priority, failure mode, and observable outcome.
3. Inspect existing coverage and select the cheapest deterministic test level
   that proves each risk: unit, integration, contract, component, or end-to-end.
4. Specify the test target, setup, action, assertions, edge cases, and likely
   files for every recommended test. Prefer fast focused tests over broad
   suites.
5. Mark behavior that cannot be proven reliably by automation as an evidence
   exception and explain why. Do not design video workflows.

## Output

Return one test-scope packet containing:

- requested behavior, acceptance criteria, repository baseline, and assumptions
- affected behavior and consumer map
- ordered risk register with stable ID, priority, failure mode, and impact
- existing coverage mapped to risk IDs
- recommended tests mapped to risk IDs, including level, target, setup,
  assertions, edge cases, expected speed, and candidate files
- excluded areas, evidence exceptions, unknowns, and blockers

Do not plan production changes, edit files, implement tests, execute checks, or
claim coverage from tests that were not inspected.
