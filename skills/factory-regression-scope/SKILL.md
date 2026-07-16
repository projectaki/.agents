---
name: factory-regression-scope
description: "Use when the human explicitly requests regression scoping or when factory-verify invokes it for a completed implementation. Inspect the full change set, trace affected behavior across the platform, and produce an executable list of manual regression test cases for evidence collection and the draft PR without running them."
---

# Factory Regression Scope

Turn a change set into a complete manual test plan for `$factory-evidence` and
the draft PR. Remain read-only.

## Workflow

1. Establish the exact base, head, and complete diff. Read the task, plan,
   implementation context, repository instructions, and relevant tests.
2. Inventory every changed file, symbol, behavior, configuration, schema, flag,
   and shared dependency. Trace callers, consumers, routes, endpoints, jobs,
   state, permissions, and data boundaries beyond the edited files.
3. Derive direct and plausible adjacent regressions across the platform. Include
   UI journeys, API requests, CLI or worker behavior, roles, states, failures,
   and cross-surface interactions when supported by the change graph.
4. Convert each material risk into an independently executable manual test case
   with one clear purpose and observable outcome. Cover distinct roles, states,
   failure paths, and cross-surface effects as separate cases when they require
   different setup, actions, or proof.
5. Deduplicate and prioritize cases by impact and likelihood. Exclude behavior
   already proven by automation unless a material user-facing or integration
   risk still requires manual observation.

## Output

Return one regression-scope packet containing:

- base, head, change summary, and assumptions
- changed files and symbols mapped to affected behavior and consumers
- an ordered manual-test summary with stable ID, priority, surface, test-case
  title, and risk covered
- one complete specification per manual test ID: rationale, preconditions,
  environment and fixtures, numbered steps or sanitized commands, expected
  result, evidence to capture, cleanup, and any approval prerequisite
- initial status `not-run` for every case; only `$factory-evidence` records the
  observed result
- coverage map from every affected behavior to one or more manual test IDs
- intentionally excluded areas, automation coverage, unknowns, and blockers

Keep IDs and titles concise and suitable for reuse unchanged in the evidence
manifest, verification report, and draft PR. Do not execute cases, modify files,
or claim unaffected behavior without tracing it. If the full change set is
unavailable, return the precise blocker.
