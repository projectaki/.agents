---
name: factory-context
description: "Use only when the human explicitly starts the context lifecycle for a software task, bug, feature, refactor, UI change, or investigation to clarify the request, gather evidence, define acceptance criteria, classify risk, and produce a readiness packet."
disable-model-invocation: true
---

# Factory Context

Turn the request into a clear task and a compact context packet before planning
or implementation.

## Input

Require a human-provided task request and the repository or worktree in scope.
Use any supplied issue, screenshots, logs, links, constraints, and prior evidence
as optional input. If the request is too ambiguous to investigate safely, return
the missing questions as the lifecycle output.

## Environment Policy

- Use environment-native tools and suitable subagents only when delegation is
  authorized by the user and repository policy and they are available under the
  current runtime and permissions.
- Treat delegation as an optimization. If subagents or a named role are
  unavailable, perform that role in the main session and report the omission.
- If a subagent lacks permissions or tools needed for execution, keep its
  read-only analysis and perform the execution in an authorized capable session.
- Treat browser, simulator, device, GUI, network, and other access-controlled
  tools as conditional. Use Playwright only when it and the target are reachable
  without permission, sandbox, or access-control failures.
- Make at most one cheap availability check and one ordinary attempt. If a tool
  is missing or access is clearly denied, stop retrying. Do not install tools or
  seek elevated access solely for optional evidence.
- Use reachable alternatives when useful and report the skipped check, concrete
  reason, evidence gap, and residual risk. An application failure observed
  through an available tool is evidence, not an access failure.

## Workflow

1. Cover the `requirements-analyst` and `context-researcher` roles, delegating
   in parallel when authorized and supported or performing them in the main
   session otherwise.
2. Add the `user-simulator` role for user-visible behavior when feasible.
3. Use the user's task plus repository state and instructions.
4. Gather local, visual, and external context needed to establish readiness.
5. Synthesize one concise context packet in the main session.

For bug reports, include expected behavior, observed behavior, environment,
known reproduction steps, frequency, existing evidence, and safety constraints.

## Visual Context

- When collecting new screenshots or video, follow `$capture-pr-evidence` as a
  supporting workflow. Rehearse before recording, capture distinct meaningful
  states, and keep temporary artifacts outside the repository.
- For web UI context, prefer Playwright navigation, snapshots, and screenshots
  when the environment policy permits it.
- Use available browser tooling, existing screenshots, HTTP/CLI flows, logs, or
  static inspection as alternatives when they provide meaningful evidence.
- For iOS simulator evidence, first confirm the host is macOS (`Darwin`) and the
  simulator is accessible. Otherwise skip it under the environment policy.
- Missing optional visual evidence does not block intake. Record the gap. If
  visual evidence is required to understand an acceptance criterion, return
  `needs-clarification` or `blocked` instead of declaring readiness.

## Output

Return:

- task summary
- expected behavior or desired outcome
- acceptance criteria
- non-goals
- likely affected areas
- relevant files and docs
- visual context and evidence, when feasible
- risk class
- assumptions and open questions
- skipped tools, reasons, evidence gaps, and residual risk
- readiness verdict: `ready`, `needs-clarification`, `blocked`, or `reject`

## Stop Condition

Stop when the context packet and readiness verdict are complete, or when the
smallest blocking questions have been identified. Return the packet to the
human. Do not invoke another factory skill, start planning or replication, or
continue into another lifecycle.

If the task is not ready, stop and ask for the smallest set of clarifications.
