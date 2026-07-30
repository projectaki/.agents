---
name: factory-test-scope
description: "Use when the human explicitly starts pre-development test scoping before factory-plan. Trace stable behavioral paths and choose the cheapest sufficient inspection, automated, or exceptional visual evidence without editing files or running tests."
---

# Factory Test Scope

Define the smallest reliable pre-implementation coverage. Remain read-only.

When orchestrated, the primary thread must delegate this skill to the routed
tier worker. That worker must not spawn another lifecycle actor.

## Input

Read the behavior, acceptance criteria, context, repository instructions,
architecture, and existing tests. Return the exact blocker if behavior is
materially undecided.

## Workflow

1. Group the change into stable behavioral path IDs. Trace each path from its
   highest relevant caller through logic, APIs, data, permissions, jobs,
   configuration, consumers, and UI to the observable result.
2. Give each direct or plausible adjacent risk a stable ID, priority, failure
   mode, and observable outcome.
3. Inspect coverage. For each path and risk, choose the highest reliable
   observable boundary and cheapest sufficient proof. Use a 1-sentence
   inspection claim plus an available corroborating signal only for simple
   non-behavioral or behavior-preserving work; otherwise choose unit,
   integration, contract, component, or end-to-end automation.
4. For each test, specify target, setup, action, assertions, edge cases, and
   likely files. Prefer focused tests.
5. Mark evidence exceptions only when automation cannot prove the behavior;
   explain why. Do not design video workflows.

State current intended behavior. Omit superseded requirements, discarded
ideas, and decision history unless still a compatibility constraint or risk.

## Output

Return an agent packet with:

- behavior, criteria, baseline, and assumptions
- affected behaviors and consumers
- paths, change category, observable boundary, and planned proof
- ordered risks with ID, priority, failure mode, and impact
- existing coverage and recommended tests mapped to risks
- each test's level, target, setup, assertions, edge cases, expected speed, and
  candidate files
- exclusions, evidence exceptions, unknowns, and blockers

When orchestrated, also write one human `report.md` using behavior and risk
names, not IDs or wide matrices. Use a short subsection per behavior when a
table would exceed 4 columns.

Do not plan production changes, edit, implement tests, run checks, or claim
coverage from uninspected tests.
