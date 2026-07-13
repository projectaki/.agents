---
name: factory-plan
description: "Use only when the human explicitly starts the planning lifecycle and supplies a context packet plus a replication packet for bugs, to produce the smallest maintainable implementation or investigation plan, verification strategy, risks, alternatives, and blockers without editing files."
disable-model-invocation: true
---

# Factory Plan

Create an explicit plan after the task is understood and before implementation.

## Input

Require a human-approved context packet or equivalent task definition. For a
bug, also require the replication packet or an explicit human decision to plan
without one. Accept repository instructions, architecture constraints, and risk
decisions as additional input. If required input is absent or contradictory,
return the gap instead of planning from assumptions.

## Environment Policy

- Delegate to an available `architect-planner` or equivalent role only when
  delegation is authorized by the user and repository policy. Otherwise plan in
  the main session.
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

## Workflow

1. Read the context packet and repository instructions.
2. For a bug, read the human-supplied replication packet and preserve its
   baseline.
3. Cover the architect-planner role through authorized delegation or in the
   main session.
4. Produce the smallest maintainable plan and verification strategy.

Gate bug planning on the replication verdict:

- `reproduced`: plan from the captured baseline
- `not-reproduced`: plan investigation or instrumentation unless the human
  explicitly accepts proceeding from the report alone
- `inconclusive`: plan only the clarification, environment work, or
  instrumentation needed to reach a trustworthy verdict
- `blocked`: stop for the missing authority, access decision, or explicit human
  risk decision before creating an implementation plan

## Planning Rules

- Preserve existing architecture and slice boundaries.
- Avoid speculative abstractions and unrelated refactors.
- Include targeted tests and verification.
- For web UI changes, include Playwright evidence only under the environment
  policy; consider tests, HTTP/CLI flows, logs, or manual steps as alternatives.
- Include iOS simulator verification only on macOS when simulator access is
  expected to work without access-control issues.
- Call out risks, assumptions, blockers, and rollback or recovery for risky work.

## Output

Return:

- plan summary and implementation steps
- expected files, slices, or subsystems touched
- architecture constraints
- required and optional verification steps
- tool assumptions, fallbacks, and expected evidence gaps
- risks and mitigations
- alternatives rejected
- rollback or recovery notes, when relevant
- blockers or human questions

## Stop Condition

Stop when the plan and its blockers or human decisions are explicit, or when an
unresolved product, architecture, security, or access decision prevents a safe
plan. Return the plan packet to the human. Do not edit files, invoke another
factory skill, start implementation, or continue into another lifecycle.

Stop if the plan depends on unresolved product, architecture, security, or
access decisions.
