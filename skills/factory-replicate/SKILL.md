---
name: factory-replicate
description: "Use only when the human explicitly starts the replication lifecycle for a reported bug. Reproduce the unchanged failure, minimize the steps, capture a safe pre-fix baseline, and report confidence without diagnosing or fixing it."
disable-model-invocation: true
---

# Factory Replicate

Create a trustworthy pre-fix bug baseline.

## Need

A bug context packet with expected and observed behavior, environment, known
steps, evidence, and safety limits. Reject non-bug work or report missing input.

## Do

1. Read the context and repository instructions.
2. Choose the smallest safe reproduction surface.
3. Reproduce without editing product code. Make at most three attempts unless
   the context justifies another limit.
4. Record the exact environment, inputs, steps, result, frequency, and evidence.
5. Minimize reliable steps and identify the observed boundary. Label unproven
   causes as hypotheses.
6. Follow `$capture-pr-evidence` for new screenshots or video.
7. Sanitize evidence and keep temporary artifacts outside tracked files.

Spawn one `bug-reproducer` subagent. For visible behavior, also spawn one
`user-simulator`. If repository policy or the runtime prevents spawning,
perform the roles in the main session and report the omission. For conditional
tools, make one availability check and one attempt, then use a reachable
fallback. Do not install tools or seek elevated access only for optional
evidence. If an inaccessible condition is essential, return `inconclusive` or
`blocked`, not `not-reproduced`.

Get human approval before destructive, irreversible, credentialed,
production-data, or externally consequential steps.

## Verdicts

- `reproduced`: the failure occurred with reliable evidence.
- `not-reproduced`: a representative reachable environment did not show it.
- `inconclusive`: the evidence or environment was insufficient.
- `blocked`: a required condition could not be accessed safely.

## Return

- verdict, expected/actual behavior, environment, and preconditions
- minimal steps, attempts, frequency, and confidence
- evidence locations, redactions, retention, and cleanup
- skipped methods, evidence gaps, safety limits, and residual risk
- observed boundary, labeled hypotheses, and needed human decisions

## Stop

Return the replication packet. Do not diagnose beyond the evidence, edit product
code, implement a fix, or start another lifecycle.
