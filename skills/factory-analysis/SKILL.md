---
name: factory-analysis
description: "Analyze supplied software-change requirements and evidence. Return system impact, behavioral paths, risks, and the smallest sufficient proof requirements without selecting an implementation or editing files."
---

# Factory Analysis

## Purpose

Determine the impact, risks, and proof requirements for a proposed change.

## Inputs

Require a task contract and current evidence packet. Require a reproduction
result when the change addresses a reported bug. Return the exact blocker when
an input is missing, stale, or contradictory.

## Operation

1. Trace each affected behavior from its highest relevant caller to the
   observable result. Include data, permissions, side effects, integrations,
   and consumers.
2. Identify affected surfaces, seams, dependencies, unknowns, and direct or
   adjacent regression risks.
3. Group the change into stable behavioral paths. Give material risks stable
   identifiers for traceability.
4. Inspect existing coverage. Map every path, acceptance criterion, and risk to
   the cheapest sufficient proof. Use inspection for simple non-behavioral
   work. Otherwise require focused automated tests. Require visual evidence
   only when automation cannot prove the property.
5. State implementation and verification constraints without selecting an
   implementation approach.
6. Produce a complete acceptance-proof record. Preserve supplied claims and
   their required proof. Add path and risk identifiers. Close the inventory for
   every universal claim or return a blocker when it cannot be bounded.

## Outputs

Return a structured result and a concise human summary with:

- system impact, affected behavior, seams, dependencies, and consumers
- behavioral paths and observable outcomes
- ordered risks, failure modes, impact, and uncertainty
- existing coverage and required tests or evidence
- acceptance criteria and risks mapped to required proof
- complete updated acceptance-proof record
- assumptions, exclusions, unknowns, blockers, and implementation constraints
- status: `ready`, `needs-input`, or `blocked`

Keep stable identifiers and complete mappings in the structured result. Use
plain behavior and risk names in the human summary.

## Side effects

Read supplied sources and the repository. Make no file or external-system
changes.

## Failure results

Return `needs-input` for a missing human decision. Return `blocked` for missing,
stale, contradictory, or inaccessible required evidence.

## Non-goals

Do not select production changes, edit files, implement tests, or run checks.
