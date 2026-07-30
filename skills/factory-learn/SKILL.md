---
name: factory-learn
description: "Use only when the human explicitly starts the learning lifecycle with a task outcome, failure, review rejection, incident, feedback item, or repeated mistake. Read the evidence and propose durable, actionable project knowledge without writing or changing anything."
---

# Factory Learn

## Execution boundary

When used by the orchestrator, the primary thread must spawn the tier worker
selected by routing and instruct that worker to use this skill. The primary
thread must not perform this lifecycle workflow. A tier worker executes the
workflow directly and does not spawn another lifecycle actor.

Identify knowledge worth preserving. Remain read-only.

## Workflow

1. Read the supplied outcome and supporting evidence. Inspect existing project
   guidance only as needed to detect duplication or conflicts.
2. Propose a learning only when it would prevent a repeated mistake, preserve a
   decision or explicit preference, change safety or verification behavior, or
   explain a durable repository-specific constraint.
3. Keep every proposal factual, actionable, concise, and free of secrets,
   sensitive logs, transient environment failures, and speculation.
4. Write proposed project guidance as a standalone statement of the durable
   current rule. Use the incident or feedback as evidence for the proposal, not
   as content. Do not include the triggering mistake, prior wording, correction
   story, or phrases such as “previously” and “we learned.”

## Output

Return:

- verdict: `propose-learning` or `no-learning`
- evidence and rationale
- recommended destination, such as `AGENTS.md`, project documentation, a
  decision record, or a follow-up task
- exact proposed content or follow-up wording
- duplicates, conflicts, stale guidance, and decisions required from the user

Keep evidence and rationale outside the exact proposed content.

Do not edit files, create follow-ups, send messages, or perform external
actions. The user decides whether and where to preserve each proposal.
