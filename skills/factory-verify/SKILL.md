---
name: factory-verify
description: "Use only when the human explicitly starts final verification for a reviewed implementation with a current change-assurance report. Prove every changed path, acceptance criterion, and reviewed risk with final-revision evidence; return a PR-ready report without modifying implementation."
---

# Factory Verify

Produce final pre-PR confidence without changing implementation.

When orchestrated, the primary thread must delegate this skill to the routed
tier worker. That worker must not spawn another lifecycle actor.

## Input

Read the task, criteria, analysis, approved plan, implementation packet, current
diff, implementation review, bug baseline, and applicable visual evidence.
Require a review covering final-diff regression risks and a
`change-assurance-report.md` with base, head, fingerprint, groups, and paths
matching the final change. Missing, stale, or contradictory required input
yields `inconclusive` or `blocked`.

## Workflow

1. Reconcile every final-diff group, path, criterion, and risk ID with evidence,
   review findings, and results for the same head.
2. If a targeted unit, integration, contract, component, type, lint, build, or
   deterministic end-to-end result is missing or stale, run the smallest fast
   command that closes the gap. Do not run a broad suite when a focused command
   suffices, install tools, or create tests.
3. Accept visual evidence only for risks that require observation and only when
   its risk ID, path, and change set match. Do not invoke
   `factory-video-evidence` or run evidence workflows.
4. Treat missing, stale, failed, blocked, inaccessible, or inferred required
   evidence as unverified. Do not require video when automation proves the risk.
5. Finalize the assurance report. Give every path a verdict and durable evidence.
   Inspection needs a concise reason and available corroborating signal.
   Exceptions block until the human accepts their residual risk.
6. Return the agent packet and human report defined in
   [references/pr-confidence-report.md](references/pr-confidence-report.md).

Keep IDs, fingerprints, and full mappings in the packet and assurance report.
Name behaviors, risks, and checks directly in `report.md`. Report only current
scope, evidence, and gaps. Follow the shared pattern in
`../factory-handoff/references/human-report-patterns.md` and use its
Verification guidance.

## Verdicts

- `pass`: the complete diff, every path and criterion, and every material risk
  have current evidence or a human-accepted exception; no blocking finding or
  known regression remains.
- `fail`: a criterion, required check, or required observed workflow fails.
- `inconclusive`: required evidence is missing, stale, or inaccessible.
- `blocked`: verification cannot proceed safely or access a requirement.

Distinguish supplied results from checks run here. Mark remote CI `pending`.
Say “no regressions observed in the verified scope,” never that regressions are
impossible.

Stop after the report. Do not fix, create a PR, merge, release, or start another
lifecycle.
