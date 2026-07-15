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

- Delegate to an available `architect-planner` or equivalent role only when
  delegation is authorized by the user and repository policy. Otherwise plan in
  the main session.
- When the human requests Claude planning or plan review, spawn a named
  `architect-planner` or `plan-reviewer` subagent and have it use `$claude-cli`.
  Relay its sanitized progress and answer text while it runs; do not invoke
  Claude as a buffered process in the root session.
- If a delegated role lacks permissions or tools needed for a planned check,
  keep its analysis and assign execution to an authorized capable session.
- Treat browser, simulator, device, GUI, network, and other access-controlled
  tools as conditional. Plan Playwright only when it and the target are expected
  to be reachable without permission, sandbox, or access-control failures.
- Mark each verification step as required or optional. Include a reachable
  fallback and the expected evidence gap for conditional checks.
- Do not plan installation or elevated access solely to obtain optional
  evidence. A required inaccessible check must remain a blocker or human risk
  decision, never an assumed pass.

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

When delegation is authorized, spawn one `architect-planner` subagent. If
repository policy or the runtime prevents spawning, plan in the main session and
report the omission.

## Return

- summary and ordered implementation steps
- expected files, slices, or systems touched
- architecture constraints
- required and optional verification, fallbacks, and evidence gaps
- risks, mitigations, rejected alternatives, and rollback notes
- blockers or human decisions

## Stop

Return the plan or blocker. Do not edit files or start another lifecycle.
