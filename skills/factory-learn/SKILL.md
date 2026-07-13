---
name: factory-learn
description: "Use only when the human explicitly starts the learning lifecycle with a task outcome, failure, review rejection, incident, or repeated mistake, to capture durable learnings without preserving transient environment failures as project facts."
disable-model-invocation: true
---

# Factory Learn

Capture only task knowledge that should affect future work.

## Input

Require a human-selected task outcome, verification failure, review finding,
incident, feedback item, or repeated mistake to evaluate. Accept relevant task
packets and repository documentation as supporting evidence. If no durable
candidate is supplied or discovered within that scope, return that no memory
change is needed.

## Workflow

1. Inspect the outcome, replication and verification evidence, review findings,
   human feedback, and incident notes.
2. Decide whether the learning is durable enough to store.
3. Update the smallest appropriate place:
   - project `AGENTS.md` for repository-specific conventions or pitfalls
   - docs for workflow, architecture, or operational knowledge
   - decision records for durable choices
   - follow-up tasks for important work not completed now
4. Avoid duplicating global engineering rules.
5. Keep entries concise, factual, and actionable.

## Promotion Criteria

Promote a learning only when it:

- prevents a repeated mistake
- documents a decision
- changes verification or safety policy
- explains a non-obvious repository constraint
- captures an explicit human preference

Record missing tools, sandbox restrictions, or access-control failures only
when they are repository-specific and likely to recur. Do not turn transient
host or session limitations into permanent project facts. Recommend a follow-up
only when omitted mandatory evidence remains operationally important.

## Output

Return:

- whether durable memory was needed
- files updated, if any
- follow-up tasks created or recommended
- stale memory noticed
- unresolved process gaps

## Stop Condition

Stop when the durable-memory decision and any scoped documentation changes are
complete, or when no durable learning is justified. Return the learning packet
to the human. Do not create or start another lifecycle automatically; any
recommended follow-up remains a human decision.

Do not store secrets, credentials, raw sensitive logs, or speculation.
