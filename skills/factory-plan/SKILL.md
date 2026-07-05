---
name: factory-plan
description: "Use after intake/context for a software-factory task to create the smallest maintainable implementation plan, expected touch points, verification strategy, risks, alternatives, and blockers before editing files."
---

# Factory Plan

Use this skill after the task is understood and before implementation starts.

## Workflow

1. Do not edit files.
2. Read relevant `AGENTS.md` files and repo docs.
3. Spawn `architect-planner`.
4. Keep the subagent read-only.
5. Provide the task/context summary and ask for a small implementation plan.
6. Synthesize the plan in the main thread.

## Planning Rules

- Prefer the smallest change that satisfies the task.
- Preserve existing architecture and slice boundaries.
- Avoid speculative abstractions and unrelated refactors.
- Include tests and verification in the plan.
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
