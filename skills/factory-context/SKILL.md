---
name: factory-context
description: "Use only when the human explicitly starts the context lifecycle for a software task, bug, feature, refactor, UI change, or investigation. Clarify the request, gather evidence, define acceptance criteria, assess risk, and return a readiness packet."
disable-model-invocation: true
---

# Factory Context

Turn a request into a task that is ready to plan or reproduce.

## Need

- The human's request.
- The repository or worktree.
- Any supplied issues, evidence, constraints, or links.

## Do

1. Read the request, repository instructions, relevant code, docs, and evidence.
2. Clarify the desired outcome, acceptance criteria, non-goals, affected areas,
   risks, assumptions, and open questions.
3. For bugs, also capture expected and observed behavior, environment, known
   steps, frequency, evidence, and safety limits.
4. For user-visible work, gather visual context when useful. Follow
   `$capture-pr-evidence` for new screenshots or video and include its handoff in
   the context packet.
5. Return the smallest complete packet and a readiness verdict.

Spawn one `requirements-analyst` and one `context-researcher` subagent in
parallel. For visible behavior, also spawn one `user-simulator`. If repository
policy or the runtime prevents spawning, perform the roles in the main session
and report the omission. Treat browser, simulator, device, GUI, and network
tools as conditional: make one availability check and one attempt, then use a
reachable fallback. Do not install tools or seek elevated access only for
optional evidence. Report skipped evidence and residual risk.

## Return

- summary, desired outcome, acceptance criteria, and non-goals
- affected areas, relevant files/docs, and visual evidence
- risk, assumptions, open questions, and evidence gaps
- verdict: `ready`, `needs-clarification`, `blocked`, or `reject`

If missing evidence is required to understand an acceptance criterion, do not
return `ready`.

## Stop

Return the packet or the smallest blocking questions. Do not plan, reproduce,
or implement the task.
