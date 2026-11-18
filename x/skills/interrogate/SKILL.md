---
name: interrogate
description: Adversaries try to break a change or a design, and only findings that a run proves survive. Use for "interrogate", "adversarial review", "challenge this", "stress test this", or "find blind spots".
---

# Interrogate

Adversaries try to break a change or a design. A finding survives only when a run proves it. Report the findings. Do not apply fixes.

## Frame

The scope is what the user names. Otherwise it is the branch diff from its merge base with the base branch, through the working tree. State the intent in your own words, from the user's message, the commits, and the pull request description. Ask the user when the intent is unclear.

## Fan out

Run Phase A steps 3 and 4 and Phase B of the **arena** skill, with three changes. Copy the scope's uncommitted changes into each worktree. Start each adversary as a worktree subagent that is an x-agent. In place of the arena task and rationale, give each adversary the scope, the intent, and this brief:

> Break this change. Prove each finding with a run against the real code, such as a failing test, a reproduction script, or command output that shows the wrong behavior. For a design or a plan, run a prototype or probe the current tree. Keep reproductions in your own worktree. Report each finding with a title, the exact command, the output that it printed, and the output that the intent requires. Leave out anything that you did not run. That includes style, naming, structure, and risks that need a future change to matter. No findings is a valid result.

## Verify

Verify each finding according to arena Phase F, by running its command again. Keep a finding when the output shows the failure and the failure breaks the intent. Drop the rest. Merge findings that have the same root cause.

Skip arena Phases C, D, and E. Adversaries find different failures, so the result keeps every verified finding, not one adversary's list.

## Output

- **Intent**: your restatement.
- **Findings**: for each verified finding, the command, its output, how it breaks the intent, and the adversaries that found it. Say "no verified findings" when none survive.
- **Dropped**: for each adversary, the number of dropped findings and why.
