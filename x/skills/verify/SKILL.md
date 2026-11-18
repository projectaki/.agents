---
name: verify
description: Prove that a change works by driving the real app the way a user does, in a browser, a mobile app, a desktop app, or a terminal, and capture the evidence.
---

# Verify

Check the change where it runs, the way a user uses it. A passing test suite is not proof that a change works.

## Choose the check

If the project has its own verification harness or a `verify-*` skill, use it first. Otherwise, match the check to the change:

| Change | Check it with |
| --- | --- |
| Web UI or Electron app | the **agent-browser** skill |
| Mobile app | the **maestro-local-tests** skill |
| CLI or TUI | run the command directly. For an interactive program, use the **tmux** skill |
| Other desktop app | the **screenshot** skill |
| Parser or migration | replay a saved real input |
| Performance | compare profiles from before and after the change |
| Storage | read back the value that was written |

If the change touches two surfaces, check both. If you cannot reach a surface, say which surface, and why, and report it as a gap.

## Check

1. Start the app from the task's worktree. Wait until it is ready.
2. For a bug, reproduce it before the fix. Save the evidence.
3. Run each success criterion as a user would: the same input, the same clicks, the same commands.
4. Save the evidence for each criterion: a screenshot for UI, the exact output for a CLI or an API. Save it in one folder for the task, and name each file after its criterion.
5. A result that does not show the criterion either way is not a pass. Neither is a check on another surface. Report it as a gap.

## Report

For each criterion: what you did, the evidence path, and pass, fail, or gap. For a bug: the evidence before the fix and after it.
