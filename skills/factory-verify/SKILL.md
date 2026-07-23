---
name: factory-verify
description: "Use only when the human explicitly starts final verification for a completed implementation with a current factory-regression-scope packet. Evaluate acceptance criteria and scoped risks against current evidence, run only targeted fast existing checks when needed, and return a PR-ready confidence report without modifying implementation."
---

# Factory Verify

Produce the final pre-PR confidence report. Do not modify the implementation.

## Input

Read the task, acceptance criteria, context, approved plan, implementation
packet, current diff, review result, bug baseline, current
`$factory-regression-scope` packet, and available manual or video evidence when
applicable. The packet's base, head, and diff fingerprint must match the final
change set. Missing, stale, or contradictory required input makes the verdict
`inconclusive` or `blocked`.

## Workflow

1. Map every acceptance criterion and regression risk ID to implementation
   evidence, review findings, and automated results for the same head.
2. When an existing targeted unit, integration, contract, component, type,
   lint, build, or deterministic end-to-end check is missing or stale, run the
   smallest fast command that resolves the gap. Do not run broad suites when a
   focused command suffices, install unavailable tools, or create tests.
3. Accept manual or video evidence only for risks explicitly requiring
   observation. Reuse video results only when their risk ID and change set
   match. Do not invoke `$factory-video-evidence` or execute evidence workflows.
4. Treat missing, stale, failed, blocked, inaccessible, or inferred required
   evidence as unverified. A missing video is not a gap when automation proves
   the risk.
5. Return the verification packet and the PR-ready report from
   [references/pr-confidence-report.md](references/pr-confidence-report.md).

## Verdict

- `pass`: every acceptance criterion and material regression risk is supported
  by current evidence, and no blocking finding or known regression remains.
- `fail`: an acceptance criterion, automated check, or required observed
  workflow demonstrably fails.
- `inconclusive`: required evidence is missing, stale, or inaccessible.
- `blocked`: verification cannot proceed safely or access a required condition.

Distinguish supplied results from checks run during verification and report
remote CI as `pending`. Say “no regressions observed in the verified scope,”
never that regressions are impossible.

Stop after the PR-ready verification report. Do not fix findings, create the
PR, merge, release, or start another lifecycle.
