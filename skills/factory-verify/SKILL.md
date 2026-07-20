---
name: factory-verify
description: "Use only when the human explicitly starts final verification for a completed implementation before creating a pull request. Prove every acceptance criterion, assess regression confidence from supplied UI workflow evidence and existing automated results, and return PR-description-ready results without running evidence workflows or test suites."
---

# Factory Verify

Produce the final pre-PR confidence report. Do not modify the implementation.

## Input

Read the task, acceptance criteria, context, approved plan, implementation
packet, current diff, review result, bug baseline, regression-scope packet, and
available video-evidence results when applicable. Missing or contradictory
required input makes the verdict `inconclusive` or `blocked`.

## Workflow

1. Map every acceptance criterion to implementation evidence and the automated
   test results already recorded by `$factory-implement`. Do not rerun unit,
   integration, or CI suites; CI will run after PR creation.
2. Invoke `$factory-regression-scope` on the complete change set. Reuse only
   supplied video-evidence results that match its workflow IDs and current
   change set. Do not invoke `$factory-video-evidence` or execute UI workflows.
3. Reconcile acceptance criteria, implementation evidence, review findings,
   prior test results, the complete UI-workflow inventory, and observed
   evidence. Preserve every workflow ID and account for each exactly once.
   Treat missing, stale, failed, blocked, or inferred required evidence as
   unverified.
4. Return the verification packet and the PR-ready report from
   [references/pr-confidence-report.md](references/pr-confidence-report.md).

## Verdict

- `pass`: every acceptance criterion is supported, required UI workflows pass,
  and no blocking finding or known regression remains.
- `fail`: an acceptance criterion or UI regression workflow demonstrably fails.
- `inconclusive`: required evidence or prior test results are missing or stale.
- `blocked`: verification cannot proceed safely or access a required condition.

Report automated checks as supplied by implementation and remote CI as
`pending`; never imply they were rerun. Say “no regressions observed in the
verified scope,” never that regressions are impossible.

Stop after the PR-ready verification report. Do not fix findings, create the
PR, merge, release, or start another lifecycle.
