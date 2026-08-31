---
name: factory-context
description: "Research a supplied software-change brief in the codebase and relevant authoritative documentation. Return a self-contained evidence packet or the exact missing information without analyzing, planning, or implementing."
---

# Factory Context

## Purpose

Build a reliable evidence packet for a supplied software-change brief.

## Inputs

Require the task contract, linked artifacts, repository or workspace, permitted
information sources, and current external documentation when applicable.

## Operation

1. Read the complete inputs. Extract the outcome, scope, acceptance criteria,
   constraints, and open decisions.
2. Trace relevant code, tests, configuration, history, and repository
   documentation.
3. Use authoritative online sources when current external interfaces,
   libraries, standards, or behavior matter.
4. Separate confirmed facts, reasonable inferences, conflicts, and unknowns.
5. Resolve discoverable gaps. Return the smallest set of blocking questions
   when required information is not discoverable.

Include history only when it still defines behavior, compatibility, migration,
or an open decision. Omit superseded requirements, discarded approaches, and
correction history.

## Outputs

Return a structured evidence packet and a concise human summary with:

- requested change, outcome, scope, and acceptance criteria
- current behavior and relevant architecture
- relevant files, symbols, entry points, tests, observable seams, side effects,
  consumers, and documentation
- project conventions, constraints, and authoritative sources
- confirmed facts, inferences, conflicts, assumptions, unknowns, and material
  questions
- status: `ready`, `needs-input`, or `blocked`

Use plain language in the human summary. Label confirmed, likely, and unknown
information. Use technical names only when they help verification.

## Side effects

Read local and permitted remote sources. Do not change the repository or remote
systems.

## Failure results

Return `needs-input` for a missing decision or fact that the caller can supply.
Return `blocked` when a required source is inaccessible.

## Non-goals

Do not analyze impact, select an implementation, create a plan, or implement.
