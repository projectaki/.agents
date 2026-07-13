---
name: factory-verify
description: "Use after implementation or during bug reproduction to verify behavior with tests, builds, lint, Playwright browser flows, app/CLI flows, logs, screenshots, and explicit evidence; treat unrun checks as unknown."
disable-model-invocation: true
---

# Factory Verify

Use this skill to prove behavior before review or merge.

## Workflow

1. Read the task, approved plan, and current git diff.
2. Spawn `verification-engineer`.
3. Spawn `user-simulator` for UI, CLI, mobile, API, workflow, or user-visible
   behavior.
4. Run targeted checks first, then broader checks required by the repo.
5. Capture concise evidence.
6. Synthesize one verification packet in the main thread.

## Visual Verification

- For web UI behavior, use the `$playwright` skill and `playwright-cli` for
  navigation, snapshots, interactions, and screenshots.
- For iOS simulator screenshots, first check `uname -s`. Only use simulator
  tooling on macOS (`Darwin`). On Linux, do not try simulator commands.
- Capture before/after screenshots when reproducing and fixing visible bugs.
- Treat missing visual evidence for user-visible work as residual risk unless
  the human accepts the exception.

## Verification Rules

- Treat unrun checks as unknown, not passed.
- Distinguish changed-code failures from pre-existing or environment failures.
- Prefer externally observable behavior for user-facing changes.
- Include exact commands or steps for reproducibility.
- Do not mark verification complete when key checks are skipped without human
  acceptance.

## Output

Return:

- verification verdict: pass, fail, inconclusive, or blocked
- commands or methods run
- user-level scenarios tested
- screenshots or visual evidence for user-visible behavior, when feasible
- results and evidence
- failures and likely cause
- skipped checks and rationale
- residual risk
- recommended next action
