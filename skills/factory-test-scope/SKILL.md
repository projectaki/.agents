---
name: factory-test-scope
description: "Use when the human explicitly starts pre-development test scoping for a proposed change before factory-plan. Trace stable behavioral paths through the existing codebase and select the cheapest sufficient inspection, automated, or exceptional visual evidence without editing files or running tests."
---

# Factory Test Scope

Define the smallest reliable test coverage for a proposed change before
implementation. Remain read-only.

## Input

Read the requested behavior, acceptance criteria, context, repository
instructions, relevant architecture, and existing tests. If the intended
behavior is materially undecided, return the precise blocker.

## Workflow

1. Group the intended change into stable behavioral path IDs. Trace each path
   from its highest relevant caller through domain logic, APIs, data,
   permissions, jobs, configuration, shared consumers, and UI boundaries to
   its observable result.
2. Identify direct and plausible adjacent regression risks. Assign each a
   stable risk ID, priority, failure mode, and observable outcome.
3. Inspect existing coverage and select the highest reliable observable
   boundary and cheapest sufficient evidence for each path and risk. Use a
   one-sentence inspection claim plus an available corroborating signal for
   simple non-behavioral or behavior-preserving work. Otherwise select unit,
   integration, contract, component, or end-to-end automation.
4. Specify the test target, setup, action, assertions, edge cases, and likely
   files for every recommended test. Prefer fast focused tests over broad
   suites.
5. Mark behavior that cannot be proven reliably by automation as an evidence
   exception and explain why. Do not design video workflows.

Use request context to determine the intended behavior, then state that behavior
directly. Do not include superseded requirements, corrected misunderstandings,
discarded test ideas, or a narrative of how the scope was reached. Include
history only when it defines a current compatibility constraint or risk.

## Output

Return one test-scope packet containing:

- requested behavior, acceptance criteria, repository baseline, and assumptions
- affected behavior and consumer map
- stable behavioral paths, change category, highest reliable observable
  boundary, and planned proof
- ordered risk register with stable ID, priority, failure mode, and impact
- existing coverage mapped to risk IDs
- recommended tests mapped to risk IDs, including level, target, setup,
  assertions, edge cases, expected speed, and candidate files
- excluded areas, evidence exceptions, unknowns, and blockers

Do not plan production changes, edit files, implement tests, execute checks, or
claim coverage from tests that were not inspected.
