---
name: factory-verify
description: "Use only when the human explicitly starts the verification lifecycle and supplies the task, approved plan, implementation packet, and relevant bug baseline, to run every applicable CI validation check, verify behavior with observable evidence, and produce a PR-ready scope and regression-confidence report while treating unrun checks as unknown."
disable-model-invocation: true
---

# Factory Verify

Prove implemented behavior within this lifecycle. Initial bug reproduction is
outside this lifecycle.

## Input

Require the task and acceptance criteria, approved plan, implementation packet,
current branch or diff, and repository verification instructions. For a bug fix,
also require the applicable replication baseline. If the evidence needed to
define verification is missing, return `inconclusive` with the input gap.

Also require access to the repository's CI definitions and any referenced local
scripts, reusable workflows, composite actions, task runners, or build images.

## Environment Policy

- Cover the `verification-engineer` role and add `user-simulator` for
  user-visible behavior. Delegate only when authorized by the user and
  repository policy and suitable subagents are available; otherwise perform
  those roles in the main session.
- Treat read-only or otherwise capability-restricted subagents as analysis
  support. Run tool-dependent verification in an authorized capable session.
- Treat browser, simulator, device, GUI, network, and other access-controlled
  tools as conditional. Use Playwright only when it and the target are reachable
  without permission, sandbox, or access-control failures.
- Make at most one cheap availability check and one ordinary attempt. After a
  missing tool or clear access failure, stop retrying. Do not install tools or
  seek elevated access solely for optional evidence.
- Use reachable alternatives such as existing tests, HTTP requests, CLI flows,
  logs, available browser tooling, existing screenshots, or manual steps.

## Workflow

1. Read the task, approved plan, implementation summary, and current diff.
2. Inventory the CI jobs applicable to this change before running checks.
3. For a bug fix, read the human-supplied minimal replication baseline. Before
   rerunning it, re-evaluate safety and confirm that any destructive, irreversible,
   production-data, credential, or externally consequential step still has
   explicit human authority. Otherwise skip it or return `blocked`.
4. Run targeted checks first, then every applicable non-destructive CI
   validation check using the same command, version, configuration, matrix
   variant, and required service when reproducible locally.
5. Audit the CI inventory against executed checks so no applicable validation
   job or referenced command is omitted.
6. Exercise externally observable behavior when feasible.
7. Capture concise, reproducible evidence and produce the verification packet
   plus the PR confidence report.

## CI Parity Gate

Inspect CI sources such as `.github/workflows`, reusable workflows, composite
actions, `.gitlab-ci.yml`, `azure-pipelines.yml`, `Jenkinsfile`, CircleCI,
Buildkite, task-runner configuration, package scripts, and repository docs.

For the current change:

1. Resolve triggers, path filters, dependencies, job matrices, and referenced
   scripts to identify everything CI is expected to validate.
2. Build a parity table before execution with one row per applicable job and
   matrix variant.
3. Run every non-destructive validation command locally. This includes builds,
   unit and integration tests, type checks, lint, formatting checks, generated
   code checks, migration validation, security scans, packaging, and container
   builds when CI will run them.
4. Record the exact command, environment or version, result, duration when
   useful, and evidence for every row.
5. Reconcile the completed table with the CI definitions after execution.

Do not claim `pass` when an applicable CI validation check is unrun, failed, or
only inferred. Return `inconclusive` or `blocked` and identify what is needed.

Do not locally replay deploy, publish, release, production migration, credential,
or other externally consequential CI steps merely for parity. Record them as
CI-only. If such a step is required for the requested confidence decision, keep
the verdict `inconclusive` or `blocked` unless the human explicitly defines a
safe verification boundary.

Passing locally demonstrates CI parity, not that the remote CI run has passed.
State remote CI status as pending unless actual CI evidence is supplied.

## Verification Rules

- Treat unrun checks as unknown, not passed.
- Distinguish changed-code failures from pre-existing or environment failures.
- Treat CI parity checks as required, not optional. A `pass` verdict requires
  every applicable non-destructive CI validation row to pass locally.
- A skipped optional check does not fail verification; report its concrete
  reason, evidence gap, fallback, and residual risk.
- If an inaccessible check is required to establish an acceptance criterion,
  return `inconclusive` or `blocked`, never `pass`.
- For iOS simulator evidence, require macOS (`Darwin`) and reachable simulator
  access. Otherwise skip it under the environment policy.
- Capture before/after evidence for visible bug fixes when feasible.
- Sanitize evidence. Do not retain secrets, credentials, tokens, personal data,
  or sensitive production data in logs, screenshots, commands, or artifacts.

## PR Confidence Report

Use [references/pr-confidence-report.md](references/pr-confidence-report.md) to
produce a concise Markdown block that can be pasted into a pull request
description. Base confidence claims on evidence; say “no regressions observed in
the verified scope” instead of claiming regressions are impossible.

Explain:

- what changed and why
- slices, systems, contracts, users, data, and operations affected
- important behavior intentionally unchanged
- acceptance criteria and user scenarios verified
- complete CI parity results and actual remote CI status
- bug reproduction before/after evidence, when applicable
- regression risks considered and evidence that addresses each one
- skipped or CI-only checks, evidence gaps, and residual risk

## Output

Return:

- verdict: `pass`, `fail`, `inconclusive`, or `blocked`
- commands or methods run
- user-level scenarios tested
- results and evidence
- bug baseline before/after result, when applicable
- failures and likely cause
- skipped checks, reasons, fallbacks, evidence gaps, and residual risk
- decisions or remaining evidence requiring human action
- PR-ready confidence report

## Stop Condition

Stop when the verification packet and verdict are complete, or when required
evidence is unavailable and the verdict is `inconclusive` or `blocked`. Return
the packet to the human. Do not invoke review, merge, release, or another factory
skill and do not start another lifecycle.
