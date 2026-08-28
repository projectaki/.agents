---
name: factory-replicate
description: "Use only when the human explicitly starts replication for a reported bug. Reproduce the unchanged failure, minimize the steps, capture a safe pre-fix baseline, and report confidence without diagnosing or fixing it."
---

# Factory Replicate

Create a trustworthy pre-fix baseline.

When orchestrated, the primary thread must delegate this skill to the routed
tier worker. That worker owns reproduction, including the user perspective for
visible behavior, and must not spawn another lifecycle actor.

## Input

Require expected and observed behavior, environment, known steps, evidence, and
safety limits. Reject non-bug work or report missing input.

## Workflow

1. Read the context and repository instructions.
2. Choose the smallest safe reproduction surface.
3. Try without editing product code, at most 3 times unless context sets another
   limit.
4. Record environment, inputs, steps, result, frequency, and evidence.
5. Minimize reliable steps and identify the observed boundary. Label unproven
   causes as hypotheses.
6. Sanitize evidence and keep temporary artifacts outside tracked files.

For conditional tools, check once and try once, then use a reachable fallback.
Do not install tools or seek elevated access for optional evidence. If an
essential condition is inaccessible, return `inconclusive` or `blocked`, not
`not-reproduced`.

Get approval before destructive, irreversible, credentialed, production-data,
or externally consequential steps.

When the orchestrator supplies Factory telemetry context, record every
reproduction attempt, environment startup, failure, retry, recovery, and wait
with the best-effort writer. Use timestamps and one operation identity across
retries. Telemetry failure never changes the replication verdict.

## Verdicts

- `reproduced`: reliable evidence captured the failure.
- `not-reproduced`: a representative reachable environment did not show it.
- `inconclusive`: evidence or environment was insufficient.
- `blocked`: a required condition was not safely accessible.

## Output

Return:

- verdict, expected and actual behavior, environment, and preconditions
- minimal steps, attempts, frequency, and confidence
- evidence, redactions, retention, and cleanup
- skipped methods, gaps, safety limits, and residual risk
- observed boundary, hypotheses, and required user decisions

Describe the current baseline and attempt data, not issue history or discarded
ideas. Do not diagnose beyond evidence, edit product code, fix the bug, or start
another lifecycle.
