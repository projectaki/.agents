---
name: factory-learn
description: "Use after task completion, failed verification, review rejection, incident, or repeated agent mistake to capture durable software-factory learnings in AGENTS.md, docs, decisions, or follow-up tasks."
---

# Factory Learn

Use this skill when something from the task should affect future work.

## Workflow

1. Inspect the task outcome, review findings, verification failures, human
   feedback, and any incident notes.
2. Decide whether the learning is durable enough to store.
3. Update the smallest appropriate place:
   - project `AGENTS.md` for repo-specific conventions or pitfalls
   - docs for workflow, architecture, or operational knowledge
   - decision records for durable choices
   - follow-up tasks for work not completed now
4. Do not duplicate global engineering rules already present in the user's
   global `AGENTS.md`.
5. Keep entries concise, factual, and actionable.

## Promotion Criteria

Promote a learning only when it:

- prevents a repeated mistake
- documents a decision
- changes verification
- changes access or safety policy
- explains a non-obvious repo constraint
- captures explicit human preference

## Output

Return:

- whether durable memory was needed
- files updated, if any
- follow-up tasks created or recommended
- stale memory noticed
- unresolved process gaps

Do not store secrets, credentials, raw sensitive logs, or speculative memory.
