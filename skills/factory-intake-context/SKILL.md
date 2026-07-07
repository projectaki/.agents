---
name: factory-intake-context
description: "Use at the start of a software-factory task, bugfix, feature, refactor, UI/mobile/web change, or investigation to clarify the request, gather local, visual, and external context, identify acceptance criteria, classify risk, and decide whether the task is ready for planning."
---

# Factory Intake Context

Use this skill before implementation or planning. The goal is to turn a request
into a clear task and a compact context summary.

## Workflow

1. Spawn `requirements-analyst` and `context-researcher` subagents in parallel.
2. Add `user-simulator` when the task involves web, UI, mobile, CLI output,
   screenshots, layout, styling, documents, charts, or user-visible behavior.
3. Ask subagents to use the user's task plus repository state.
4. Wait for all subagents.
5. Synthesize one concise intake/context result in the main thread.

## Visual Context

- For web UI context, use the `$playwright` skill and `playwright-cli` for
  navigation, snapshots, and screenshots.
- For mobile iOS screenshots, first check `uname -s`. Only use the iOS
  simulator on macOS (`Darwin`). On Linux, do not try simulator commands.
- Capture visual evidence before planning when the task depends on visible
  behavior.

## Subagent Prompt Shape

```text
Use this task plus repository state.

Requirements analyst: clarify expected outcome, acceptance criteria, non-goals,
risk class, and readiness gaps.

Context researcher: find relevant files, existing behavior, tests, docs, logs,
external sources if needed, assumptions, and context gaps.

User simulator, when included: gather visual context and user-observable
behavior. Use `$playwright` for web. Use iOS simulator screenshots only on macOS.

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
- visual context and screenshot evidence, when applicable
- risk class
- assumptions
- open questions
- readiness verdict: ready, needs-clarification, blocked, or reject

If the task is not ready, stop and ask the human orchestrator for the smallest
set of clarifications needed.
