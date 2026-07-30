---
name: factory-verify
description: "Use only when the human explicitly starts final verification for a completed implementation with a current factory-regression-scope packet and change-assurance report. Prove every grouped behavioral path, acceptance criterion, and scoped risk with final-revision evidence, then return a PR-ready confidence report without modifying implementation."
---

# Factory Verify

## Execution boundary

When used by the orchestrator, the primary thread must spawn the tier worker
selected by routing and instruct that worker to use this skill. The primary
thread must not perform this lifecycle workflow. A tier worker executes the
workflow directly and does not spawn another lifecycle actor.

Produce the final pre-PR confidence report. Do not modify the implementation.

## Input

Read the task, acceptance criteria, context, approved plan, implementation
packet, current diff, review result, bug baseline, current
`$factory-regression-scope` packet, and available screenshot or video evidence
when applicable. Require the canonical `change-assurance-report.md`. Its base,
head, diff fingerprint, change groups, and behavioral paths must match the
final change set. Missing, stale, or contradictory required input makes the
verdict `inconclusive` or `blocked`.

## Workflow

1. Reconcile every final-diff change group, behavioral path, acceptance
   criterion, and regression risk ID with implementation evidence, review
   findings, and results for the same head.
2. When an existing targeted unit, integration, contract, component, type,
   lint, build, or deterministic end-to-end check is missing or stale, run the
   smallest fast command that resolves the gap. Do not run broad suites when a
   focused command suffices, install unavailable tools, or create tests.
3. Accept screenshot or video evidence only for risks explicitly requiring
   observation. Reuse visual results only when their risk ID, behavioral path,
   and change set match. Do not invoke `$factory-video-evidence` or execute
   evidence workflows.
4. Treat missing, stale, failed, blocked, inaccessible, or inferred required
   evidence as unverified. A missing video is not a gap when automation proves
   the risk.
5. Finalize the change-assurance report. Give every behavioral path a verdict
   and durable evidence reference. Inspection evidence requires a concise
   reason and an available corroborating signal. An exception remains blocking
   until the human explicitly accepts its residual risk.
6. Return the verification packet and the PR-ready report from
   [references/pr-confidence-report.md](references/pr-confidence-report.md).

The PR-ready report is the lifecycle's single human `report.md`. Keep stable
IDs, fingerprints, and exhaustive assurance mappings in the internal
verification packet and `change-assurance-report.md`. In the human report, name
behaviors, risks, and checks directly.

Report only the current change set, current evidence, and remaining gaps.
Earlier packets are inputs for validation, not report content. Do not narrate
superseded scope, removed risks, corrected mistakes, failed earlier attempts, or
how the report changed. Preserve stable risk IDs without recounting their
history.

## Verdict

- `pass`: the complete diff is accounted for; every behavioral path,
  acceptance criterion, and material regression risk is supported by current
  evidence or an explicitly human-accepted exception; and no blocking finding
  or known regression remains.
- `fail`: an acceptance criterion, automated check, or required observed
  workflow demonstrably fails.
- `inconclusive`: required evidence is missing, stale, or inaccessible.
- `blocked`: verification cannot proceed safely or access a required condition.

Distinguish supplied results from checks run during verification and report
remote CI as `pending`. Say “no regressions observed in the verified scope,”
never that regressions are impossible.

Stop after the PR-ready verification report. Do not fix findings, create the
PR, merge, release, or start another lifecycle.
