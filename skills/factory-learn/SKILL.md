---
name: factory-learn
description: "Identify durable project knowledge from a supplied outcome, failure, review rejection, incident, feedback, or repeated mistake. Return a learning proposal without writing or changing anything."
---

# Factory Learn

## Purpose

Identify knowledge that is worth preserving.

## Inputs

Require a task outcome and supporting evidence. Accept optional operational
observations and current project guidance. Treat missing operational
observations as an analytics gap, not a task defect.

## Operation

1. Read the outcome and supplied evidence. Inspect project guidance only to find
   duplication or conflicts.
2. Propose learning only when it preserves a decision, preference, or repository
   constraint; prevents repetition; or changes safety or verification.
3. Keep proposals factual, actionable, concise, and free of secrets, sensitive
   logs, transient failures, and speculation.
4. State each durable current rule on its own. Keep the incident, old wording,
   mistake, and correction story out of the proposed text.

## Outputs

Return a structured result and a concise human summary with:

- verdict: `propose-learning` or `no-learning`
- evidence and rationale
- proposed destination in project guidance, documentation, a decision record,
  or a follow-up
- exact proposed text
- duplicates, conflicts, stale guidance, and required human decisions

Keep evidence outside the proposed text.

## Side effects

Read supplied evidence and current project guidance. Make no changes and take
no external action.

## Failure results

Return `no-learning` when the evidence supports no durable rule. Return the
exact missing input when the supplied evidence cannot support a conclusion.

## Non-goals

Do not edit files, create follow-ups, send messages, or take external action.
