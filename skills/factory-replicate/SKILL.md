---
name: factory-replicate
description: "Reproduce a supplied bug report without changing product code. Minimize the steps, capture a safe baseline, and return the observed result, evidence, and confidence without diagnosing or fixing the bug."
---

# Factory Replicate

## Purpose

Create a trustworthy baseline for a reported bug.

## Inputs

Require expected behavior, observed behavior, environment, known steps,
available evidence, execution capabilities, and safety limits. Reject work that
does not describe a possible bug.

## Operation

1. Read the supplied evidence and repository instructions.
2. Choose the smallest safe reproduction surface.
3. Try without editing product code. Make at most three attempts unless an
   input sets another limit.
4. Record the environment, inputs, steps, result, frequency, and evidence.
5. Minimize reliable steps and identify the observed seam. Label unproven
   causes as hypotheses.
6. Sanitize evidence and keep temporary artifacts outside tracked files.

For an optional tool, check once and try once. Then use a reachable fallback.
Do not install tools or seek elevated access for optional evidence. Get human
approval before a destructive, irreversible, credentialed, production-data, or
externally consequential action.

## Outputs

Return a structured result and a concise human summary with:

- verdict: `reproduced`, `not-reproduced`, `inconclusive`, or `blocked`
- expected and actual behavior, environment, and preconditions
- minimal steps, attempts, frequency, and confidence
- evidence, redactions, retention, and cleanup
- skipped methods, gaps, safety limits, and residual risk
- observed seam, hypotheses, and required human decisions

Use `not-reproduced` only when a representative reachable environment did not
show the failure. Use `inconclusive` or `blocked` when evidence or access was
insufficient.

## Side effects

Start permitted environments. Interact with the application. Create sanitized
temporary evidence outside tracked files. Clean up as specified by the inputs.

## Failure results

Return `inconclusive` for insufficient evidence. Return `blocked` when a
required condition is not safely accessible.

## Non-goals

Do not diagnose beyond evidence, edit product code, or fix the bug.
