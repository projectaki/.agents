---
name: factory-learn
description: "Use only when the human explicitly starts learning from a task outcome, failure, review rejection, incident, feedback, or repeated mistake. Propose durable project knowledge without writing or changing anything."
---

# Factory Learn

Identify knowledge worth preserving. Remain read-only.

When orchestrated, the primary thread must delegate this skill to the routed
tier worker. That worker must not spawn another lifecycle actor.

## Workflow

1. Read the outcome and canonical evidence. When available, also read
   `telemetry/events.jsonl` or its noncanonical summary for time, failures,
   retries, recovery, waits, and interruptions. Treat missing telemetry as an
   analytics gap, not a task defect. Inspect project guidance only to find
   duplication or conflicts.
2. Propose learning only when it preserves a decision, preference, or
   repository constraint; prevents repetition; or changes safety or
   verification.
3. Keep proposals factual, actionable, concise, and free of secrets, sensitive
   logs, transient failures, and speculation.
4. State each durable current rule on its own. Keep the incident, old wording,
   mistake, and correction story out of the proposed text.

## Output

Return:

- verdict: `propose-learning` or `no-learning`
- evidence and rationale
- destination: `AGENTS.md`, project docs, a decision record, or a follow-up
- exact proposed text
- duplicates, conflicts, stale guidance, and required user decisions

Keep evidence outside the proposed text. Do not edit files, create follow-ups,
send messages, or take external action. The user decides what to preserve.
