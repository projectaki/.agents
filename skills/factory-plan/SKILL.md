---
name: factory-plan
description: "Use after intake/context for a software-factory task to create the smallest maintainable implementation plan, expected touch points, verification strategy, risks, alternatives, and blockers before editing files."
---

# Factory Plan

Use this skill after the task is understood and before implementation starts.

## Workflow

1. Spawn `architect-planner`.
2. Provide the task/context summary and ask for a small implementation plan.
3. Synthesize the plan in the main thread.

## Planning Rules

- Prefer the smallest change that satisfies the task.
- Preserve existing architecture and slice boundaries.
- Avoid speculative abstractions and unrelated refactors.
- Include tests and verification in the plan.
- For web UI changes, include Playwright screenshot/snapshot verification when
  useful.
- For iOS simulator verification, include it only when running on macOS
  (`Darwin`); on Linux, mark it unavailable instead of trying simulator access.
- Call out risks, assumptions, and blockers.
- Include rollback or recovery notes for risky work.

## Output

Return:

- plan summary
- implementation steps
- expected files, slices, or subsystems touched
- architecture constraints
- test and verification plan
- risks and mitigations
- alternatives rejected
- rollback or recovery notes if relevant
- blockers or human questions

Stop if the plan depends on unresolved product, architecture, security, or
access decisions.
