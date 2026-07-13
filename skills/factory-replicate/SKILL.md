---
name: factory-replicate
description: "Use only when the human explicitly starts the replication lifecycle for a reported bug and supplies enough context to reproduce the failure, minimize reliable steps, capture baseline evidence, and classify reproduction confidence without fixing the bug."
disable-model-invocation: true
---

# Factory Replicate

Establish a trustworthy pre-fix bug baseline. Do not use this skill for feature
work, general verification, or implementation.

## Input

Require a human-provided bug context packet or equivalent information containing
expected behavior, observed behavior, environment, known steps, available
evidence, and safety constraints. If the input describes non-bug work or lacks
essential safe reproduction details, return that mismatch or gap to the human.

## Environment Policy

- Cover the `bug-reproducer` role and add `user-simulator` when user-visible
  behavior matters. Delegate only when authorized by the user and repository
  policy and suitable subagents are available; otherwise perform those roles in
  the main session.
- Treat read-only or otherwise capability-restricted subagents as analysis
  support. Run tool-dependent reproduction in an authorized capable session.
- Treat browser, simulator, device, GUI, network, and other access-controlled
  tools as conditional. Use Playwright only when it and the target are reachable
  without permission, sandbox, or access-control failures.
- Make at most one cheap availability check and one ordinary attempt. After a
  missing tool or clear access failure, stop retrying. Do not install tools or
  seek elevated access solely for optional evidence.
- Use reachable alternatives such as tests, HTTP requests, CLI flows, logs,
  available browser tools, existing screenshots, or precise manual steps.
- If an inaccessible condition is essential to reproduction, return
  `inconclusive` or `blocked`, not `not-reproduced`.

## Workflow

1. Confirm this is a bug workflow. If not, stop with an input-mismatch verdict.
2. Read the context packet, repository instructions, expected and observed
   behavior, environment, known steps, and existing evidence.
3. Choose the smallest safe reproduction surface.
4. Reproduce the unchanged behavior without editing product code or implementing
   a fix. Keep any temporary artifacts outside tracked source files.
5. Record exact steps, inputs, environment, actual result, and evidence.
6. Repeat only when cheap and necessary. Use at most three attempts unless the
   context provides a justified different bound.
7. Minimize reliable steps and identify the observed boundary without claiming
   an unproven root cause.
8. Sanitize evidence and store only the minimum needed for reproduction. Redact
   secrets, credentials, tokens, personal data, and sensitive production data.
   Prefer temporary or repository-approved artifact locations and state cleanup
   or retention needs.
9. Produce a self-contained replication packet.

Stop and request human authority before destructive, irreversible,
production-data, credential, or externally consequential reproduction steps.

## Verdicts

- `reproduced`: the reported failure occurred with reliable evidence
- `not-reproduced`: a representative reachable environment did not exhibit it
- `inconclusive`: evidence or environment was insufficient
- `blocked`: a required condition could not be accessed safely

## Output

Return:

- verdict
- expected and actual behavior
- environment and preconditions
- minimal exact steps or commands
- frequency, attempts, and confidence
- evidence and artifact locations
- redactions, artifact retention, and cleanup needs
- attempted methods
- skipped checks, concrete reasons, evidence gaps, and residual risk
- safety limitations
- observed affected boundary and clearly labeled hypotheses
- decisions or information needed from the human

## Stop Condition

Stop when the replication packet and verdict are complete, when the bounded
attempts are exhausted, or when safety or access prevents further reproduction.
Return the packet to the human. Do not diagnose beyond the observed evidence,
implement a fix, invoke another factory skill, or start another lifecycle.

Do not edit product code, implement a fix, or claim a root cause without
evidence.
