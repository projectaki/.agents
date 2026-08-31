---
name: factory-intake
description: "Align a software-change request with the human. Accept the request and supplied artifacts, ask the smallest necessary questions, and return an agreed task contract without researching, planning, or implementing."
---

# Factory Intake

## Purpose

Align the requested software change with the human.

## Inputs

Require the request, supplied artifacts, and either direct access to the human
or a caller that can relay questions and answers.

## Operation

1. Read the request and supplied artifacts.
2. State the intended feature and requested implementation direction in plain
   language.
3. Ask the smallest set of questions needed to align behavior, scope,
   acceptance criteria, constraints, implementation preferences, authority,
   dependencies, and deliverable. Do not ask questions that the repository can
   answer.
4. Incorporate each answer. Ask again only when material ambiguity remains.
5. Return `aligned` only after the human can correct the complete task contract.
   Do not infer agreement from silence.

If direct human access is unavailable, return the exact questions. Accept the
relayed answers as additional input and continue the same operation.

## Outputs

Return a structured result and a concise human summary with:

- status: `aligned` or `needs-input`
- objective and expected behavior
- acceptance criteria
- in-scope and out-of-scope work
- implementation expectations and constraints
- authority, approvals, dependencies, and assumptions
- expected deliverable
- unanswered questions
- an acceptance-proof record with stable claim and proof identifiers, original
  required proof, and a closed inventory for each accepted universal claim

## Side effects

Ask the human questions when direct access is available. Make no repository or
external-system changes.

## Failure results

Return `needs-input` with the exact unresolved question when agreement, required
authority, or a material fact is missing.

## Non-goals

Do not research the codebase, plan, implement, or invent requirements.
