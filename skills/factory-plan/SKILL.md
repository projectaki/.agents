---
name: factory-plan
description: "Use only when the human explicitly starts the planning lifecycle with a context packet and, for bugs, a replication packet or explicit approval to proceed without one. Produce a scoped implementation and verification plan without editing files."
disable-model-invocation: true
---

# Factory Plan

Create the smallest safe plan before implementation.

## Need

- An approved context packet and repository instructions.
- For bugs, a replication packet or explicit human approval to proceed without
  one.
- Any architecture, risk, or access decisions that affect the plan.

Return missing or contradictory input instead of planning from assumptions.

## Do

1. Read the supplied packets and preserve any bug baseline.
2. Respect repository architecture and slice boundaries.
3. Plan only the requested change; avoid speculative abstractions and unrelated
   refactors.
4. Include targeted tests and verification. Mark each check `required` or
   `optional`, with a fallback and evidence gap for conditional tools.
5. State risks, assumptions, blockers, and rollback or recovery where relevant.

For bug replication verdicts:

- `reproduced`: plan from the baseline.
- `not-reproduced`: plan investigation or instrumentation unless the human
  accepts the risk.
- `inconclusive`: plan only what is needed to reach a trustworthy verdict.
- `blocked`: stop for the missing access, authority, or risk decision.

Spawn one `architect-planner` subagent. If repository policy or the runtime
prevents spawning, plan in the main session and report the omission. Do not plan
installation or elevated access solely for optional evidence.

## Return

- summary and ordered implementation steps
- expected files, slices, or systems touched
- architecture constraints
- required and optional verification, fallbacks, and evidence gaps
- risks, mitigations, rejected alternatives, and rollback notes
- blockers or human decisions

## Stop

Return the plan or blocker. Do not edit files or start another lifecycle.
