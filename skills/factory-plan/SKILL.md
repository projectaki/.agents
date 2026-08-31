---
name: factory-plan
description: "Create an implementation-ready plan from supplied requirements, evidence, impact analysis, risks, and proof requirements. Do not edit files or implement the plan."
---

# Factory Plan

## Purpose

Create the smallest complete implementation plan.

## Inputs

Require the task contract, current evidence, impact analysis, behavioral paths,
risks, acceptance-proof record, repository or workspace, and applicable human
decisions. Return the exact blocker when an input is missing, stale, or based on
different acceptance criteria.

## Operation

1. Read the supplied inputs and repository instructions.
2. Inspect only enough current code to ground the plan.
3. Define ordered and concrete implementation steps.
4. Map every supplied path and risk identifier to corroborated inspection,
   targeted automation, visual evidence only when automation is insufficient,
   or a human-approved evidence exception.
5. Record assumptions, risks, dependencies, and blockers.
6. Produce a complete updated acceptance-proof record with the planned proof.

Reject the plan when the planned method weakens or substitutes required proof
without an accepted exception for the exact claim and path. Do not let related
wording extend an exception.

Do not add unsupported requirements or speculative refactors. Describe current
requirements and constraints without revision history or discarded approaches.

## Outputs

Return a structured plan and a concise human summary with:

- objective, scope, and acceptance criteria
- current behavior and relevant architecture
- ordered steps with expected files, symbols, and logic
- relevant errors, edge cases, migrations, observability, and rollback
- risks mapped to test level, work, and expected result
- paths mapped to implementation steps and cheapest sufficient proof
- justified non-automated exceptions
- complete updated acceptance-proof record
- assumptions, risks, dependencies, blockers, and required decisions
- status: `ready`, `needs-input`, or `blocked`

For a code or system-structure change, include a design preview in the human
summary. Use a small Mermaid diagram and one or two grounded proposed code
examples. Show only key files, types, interfaces, composition, or control flow.
Keep each example below 25 lines. Return larger reusable examples as artifacts.
For a documentation or simple configuration change, state why a diagram or
code example does not help.

Keep stable identifiers and complete mappings in the structured result. Use
plain behavior and risk names in the human summary.

## Side effects

Read the repository. Create only requested planning artifacts outside product
files. Do not change product or test files.

## Failure results

Return `needs-input` for an unresolved material decision. Return `blocked` for
missing, stale, or contradictory required inputs.

## Non-goals

Do not edit product files, implement the plan, or invent a material decision.
