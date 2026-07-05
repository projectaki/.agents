---
name: factory-intake-context
description: "Use at the start of a software-factory task, bugfix, feature, refactor, or investigation to clarify the request, gather local and external context, identify acceptance criteria, classify risk, and decide whether the task is ready for planning."
---

# Factory Intake Context

Use this skill before implementation or planning. The goal is to turn a request
into a clear task and a compact context summary.

## Workflow

1. Do not edit files.
2. Read relevant `AGENTS.md` files and repo docs.
3. Spawn `requirements-analyst` and `context-researcher` subagents in parallel.
4. Keep both subagents read-only.
5. Ask both subagents to use the user's task plus repository state.
6. Wait for both subagents.
7. Synthesize one concise intake/context result in the main thread.

## Subagent Prompt Shape

```text
Use this task plus repository state. Keep read-only.

Requirements analyst: clarify expected outcome, acceptance criteria, non-goals,
risk class, and readiness gaps.

Context researcher: find relevant files, existing behavior, tests, docs, logs,
external sources if needed, assumptions, and context gaps.

Task:
<user task>
```

## Output

Return:

- task summary
- expected behavior or desired outcome
- acceptance criteria
- non-goals
- likely affected areas
- relevant files/docs
- risk class
- assumptions
- open questions
- readiness verdict: ready, needs-clarification, blocked, or reject

If the task is not ready, stop and ask the human orchestrator for the smallest
set of clarifications needed.
