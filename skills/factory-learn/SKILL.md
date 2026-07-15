---
name: factory-learn
description: "Use only when the human explicitly starts the learning lifecycle with a task outcome, failure, review rejection, incident, feedback item, or repeated mistake. Store only durable, actionable project knowledge."
disable-model-invocation: true
---

# Factory Learn

Preserve knowledge that should change future work.

## Need

A human-selected outcome, failure, finding, incident, feedback item, or repeated
mistake, plus relevant task packets or repository docs.

## Do

1. Review the evidence and decide whether the learning is durable.
2. Store it in the smallest suitable place:
   - project `AGENTS.md` for concise repository conventions or pitfalls
   - docs for workflow, architecture, or operational knowledge
   - a decision record for a durable choice
   - a follow-up task for important unfinished work
3. Keep it factual, actionable, concise, and free of duplicated global rules.

Store a learning only when it prevents a repeated mistake, records a decision,
changes safety or verification policy, explains a non-obvious repository
constraint, or captures an explicit human preference. Store environment or
access failures only when repository-specific and likely to recur. Never store
secrets, sensitive logs, or speculation.

## Return

- whether durable memory was needed
- files changed
- follow-ups created or recommended
- stale memory or unresolved process gaps noticed

## Stop

Return the learning packet, including when no change is justified. Do not start
another lifecycle; follow-up remains a human decision.
