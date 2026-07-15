---
name: factory-regression-scope
description: "Use when the human explicitly requests regression scoping or when factory-verify invokes it for a completed implementation. Inspect the full change set, trace affected behavior across the platform, and return every UI, API, or other flow that needs manual regression testing without executing tests."
---

# Factory Regression Scope

Turn a change set into the complete manual regression input for
`$factory-evidence`. Remain read-only.

## Workflow

1. Establish the exact base, head, and complete diff. Read the task, plan,
   implementation context, repository instructions, and relevant tests.
2. Inventory every changed file, symbol, behavior, configuration, schema, flag,
   and shared dependency. Trace callers, consumers, routes, endpoints, jobs,
   state, permissions, and data boundaries beyond the edited files.
3. Derive direct and plausible adjacent regressions across the platform. Include
   UI journeys, API requests, CLI or worker behavior, roles, states, failures,
   and cross-surface interactions when supported by the change graph.
4. Deduplicate and prioritize scenarios by impact and likelihood. Exclude checks
   already proven by automation unless manual behavior remains material.

## Output

Return one regression-scope packet containing:

- base, head, change summary, and assumptions
- changed files and symbols mapped to affected behavior and consumers
- ordered scenarios with ID, risk, surface, rationale, preconditions, fixtures,
  exact steps or sanitized commands, expected results, evidence to capture, and
  cleanup
- coverage map from every affected behavior to one or more scenarios
- intentionally excluded areas, automation coverage, unknowns, and blockers

Do not execute scenarios, modify files, or claim unaffected behavior without
tracing it. If the full change set is unavailable, return the precise blocker.
