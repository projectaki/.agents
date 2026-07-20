---
name: factory-regression-scope
description: "Use when the human explicitly requests regression scoping or when factory-verify invokes it for a completed implementation. Inspect the full change set, trace affected behavior, and produce compact UI regression workflows for reviewer-facing video evidence without running them."
---

# Factory Regression Scope

Turn a change set into focused UI workflows for `$factory-video-evidence` and
the draft PR. Remain read-only.

## Workflow

1. Establish the exact base, head, and complete diff. Read the task, plan,
   implementation context, repository instructions, and relevant tests.
2. Inventory every changed file, symbol, behavior, configuration, schema, flag,
   and shared dependency. Trace callers, consumers, routes, endpoints, jobs,
   state, permissions, and data boundaries beyond the edited files.
3. Derive direct and plausible adjacent regressions. Separate reviewer-visible
   UI behavior from risks better covered by automated tests.
4. Convert each material UI risk into an independently executable workflow with
   one clear purpose and observable outcome. Specify the shortest path that
   still proves the behavior. Split roles, states, and failure paths only when
   they need different setup, actions, or proof.
5. Deduplicate and prioritize workflows by impact and likelihood. Exclude
   behavior already proven by automation unless reviewers benefit from seeing
   the user-facing result.

## Output

Return one regression-scope packet containing:

- base, head, change summary, and assumptions
- changed files and symbols mapped to affected behavior and consumers
- an ordered UI-workflow summary with stable ID, priority, title, and risk
  covered
- one complete specification per workflow ID: rationale, preconditions,
  environment and fixtures, numbered UI actions, expected result, cleanup, and
  any approval prerequisite
- initial status `not-run` for every workflow; only
  `$factory-video-evidence` records the observed result
- a coverage map from reviewer-visible affected behavior to workflow IDs
- non-UI risks, automated coverage, intentionally excluded areas, unknowns,
  and blockers

Keep IDs and titles concise for video filenames, the verification report, and
the draft PR. Do not execute workflows, modify files, or claim unaffected
behavior without tracing it. If the full change set is unavailable, return the
precise blocker.
