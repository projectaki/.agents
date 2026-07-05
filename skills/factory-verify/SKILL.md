---
name: factory-verify
description: "Use after implementation or during bug reproduction to verify behavior with tests, builds, lint, browser/app/CLI flows, logs, screenshots, and explicit evidence; treat unrun checks as unknown."
---

# Factory Verify

Use this skill to prove behavior before review or merge.

## Workflow

1. Read the task, approved plan, and current git diff.
2. Spawn `verification-engineer`.
3. Spawn `user-simulator` for UI, CLI, mobile, API, workflow, or user-visible
   behavior.
4. Keep subagents read-only unless the human explicitly asks to add/fix
   verification assets.
5. Run targeted checks first, then broader checks required by the repo.
6. Capture concise evidence.
7. Synthesize one verification packet in the main thread.

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
- results and evidence
- failures and likely cause
- skipped checks and rationale
- residual risk
- recommended next action
