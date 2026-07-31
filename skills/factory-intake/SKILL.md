---
name: factory-intake
description: "Use only when the human explicitly starts intake for a software change. Ask concise questions to align on the feature, implementation expectations, scope, and success criteria; return an agreed task contract without researching, planning, or implementing."
---

# Factory Intake

Align with the human before research or planning.

When orchestrated, the primary thread delegates intake to the routed worker.
The worker must not spawn another lifecycle actor.

## Workflow

1. Read the request and supplied artifacts.
2. State the intended feature and any requested implementation direction in
   plain language.
3. Ask the human the smallest set of questions needed to align on behavior,
   scope, acceptance criteria, constraints, implementation preferences,
   authority, and deliverable. Do not ask questions answerable from the
   repository.
4. Incorporate the answers and ask again only when material ambiguity remains.
5. Return `aligned` only after the human has had an opportunity to correct the
   task contract. Do not infer agreement from silence.

If the worker cannot talk to the human directly, return the exact questions for
the primary thread to ask. Resume intake with the answers.

## Output

Return:

- status: `aligned` or `needs-input`
- objective and expected behavior
- acceptance criteria
- in-scope and out-of-scope work
- implementation expectations and constraints
- authority, approvals, dependencies, and assumptions
- expected deliverable
- unanswered questions

When orchestrated, also write one concise human `report.md` containing the
current understanding and any questions. Follow the shared pattern in
`../factory-handoff/references/human-report-patterns.md` and use its Intake
guidance. Do not research the codebase, plan, implement, or invent
requirements.
