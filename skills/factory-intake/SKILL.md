---
name: factory-intake
description: "Create the compact Factory task contract for a software change. Use when a request first enters Factory or when changed scope, authority, acceptance criteria, or deliverables require a new task revision."
---

# Factory Intake

## Purpose

Create an explicit task contract without researching or designing the change.

## Inputs

Require the request, supplied artifacts, and access to the human when a material
decision is unresolved.

## Operation

1. Extract the objective, observable behavior, acceptance criteria, scope,
   constraints, authority, and requested deliverable.
2. Treat a clear request as aligned. Do not require confirmation when no
   material ambiguity exists.
3. Ask only questions that the repository cannot answer and whose answers can
   change behavior, scope, risk, proof, authority, or delivery.
4. Keep edit, test, commit, push, and draft-pull-request authority separate.
5. Increment the task revision when accepted behavior, scope, proof, authority,
   or deliverable changes.

## Outputs

Return:

- status: `aligned` or `needs-input`
- task revision, objective, acceptance criteria, included and excluded scope
- constraints, human decisions, assumptions, and open decisions
- authority for edit, test, commit, push, and draft pull request
- requested deliverable: `local_commit` or `draft_pull_request`
- initial acceptance claims and required proof methods

## Side effects

Ask necessary questions. Make no repository or external-system changes.

## Failure results

Return `needs-input` with one exact material question when the contract cannot
be aligned safely.

## Non-goals

Do not research the repository, classify risk, plan, implement, or infer
authority.
