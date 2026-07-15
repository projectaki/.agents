---
name: factory-verify
description: "Use only when the human explicitly starts the verification lifecycle with the task, context, approved plan, implementation packet, diff, and relevant bug baseline. Verify behavior, local CI parity, and regressions with observable evidence, then return a PR-ready confidence report."
disable-model-invocation: true
---

# Factory Verify

Prove the implemented behavior. Initial bug reproduction belongs to
`$factory-replicate`.

## Need

- Task, acceptance criteria, context packet, approved plan, implementation
  packet, current diff, and repository verification instructions.
- CI definitions and their referenced scripts, workflows, actions, runners, or
  build images.
- For bugs, the replication baseline.
- When context captured visuals, its evidence run, interaction map, and manifest.

Return `inconclusive` when required verification input is missing.

Spawn one `verification-engineer` subagent. For visible behavior, also spawn one
`user-simulator`. If repository policy or the runtime prevents spawning,
perform the roles in the main session and report the omission. Run
tool-dependent checks in a capable session.

## Do

1. Read the inputs and diff.
2. Inventory every applicable CI job and matrix variant, resolving triggers,
   filters, dependencies, and referenced commands.
3. Run targeted checks, then every applicable non-destructive CI validation
   locally with equivalent versions, configuration, variants, and services.
4. Reconcile the executed checks with the inventory.
5. Exercise observable user behavior when feasible.
6. For user-visible work, follow `$capture-pr-evidence`. Reuse the context-stage
   run, interaction map, viewport, fixtures, and capture points; keep `before-*`
   immutable, create `after-*`, and explain intended differences or regressions.
7. Return the verification packet and the PR report from
   [references/pr-confidence-report.md](references/pr-confidence-report.md).

For bug baselines, recheck authorization before destructive, irreversible,
credentialed, production-data, or externally consequential steps.

## Rules

- A `pass` requires every applicable non-destructive local CI validation to pass.
  Unrun, failed, or inferred checks are not passes.
- Record deploy, publish, release, production migration, credentialed, and other
  externally consequential CI steps as `CI-only`; do not run them without human
  approval.
- Local parity does not prove remote CI passed. Report its actual status or
  `pending`.
- Distinguish failures caused by the change from existing or environment
  failures.
- For conditional tools, make one availability check and one attempt, then use a
  reachable fallback. Do not install tools or seek elevated access only for
  optional evidence.
- If a required check or visual comparison is unavailable, return
  `inconclusive` or `blocked`. Otherwise report the gap and residual risk.
- Sanitize logs and artifacts. Keep evidence outside the repository and upload
  only `publish/` contents.
- Say “no regressions observed in the verified scope,” never that regressions are
  impossible.

## Return

- verdict: `pass`, `fail`, `inconclusive`, or `blocked`
- CI inventory, exact commands/methods, and results
- user scenarios and acceptance criteria verified
- before/after evidence and bug baseline result, when applicable
- failures, skips, evidence gaps, residual risk, and human decisions
- PR-ready confidence report

## Stop

Return the verification packet. Do not review, merge, release, or start another
lifecycle.
