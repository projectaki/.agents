---
name: arena
description: Spawn several candidates in parallel at the same task, pick a base, and graft the strongest parts of the others into it. Use for "arena this", or when one attempt at a non-trivial result would lock in the wrong shape.
---

# Arena

Before you start anything, open a todo list with one item for each phase: Frame, Fan out, Cross-judge, Pick, Graft, Verify.

## Phase A: Frame

Every candidate gets the same prompt, so the prompt is the contract.

1. State the result that each candidate produces.
2. Write the rubric: 3 to 6 concrete criteria that can be graded and that define success for this task. You use it to pick in Phase D. Candidates see only the task.
3. Choose the runners: one fresh subagent on your strongest model, one on your second model, and one other-vendor model, according to the delegation reference. If a runner cannot start, drop it and say so. Keep at least two runners. Add runners when the arena covers several design directions. Use the same model several times only when the work depends on volume more than on judgment. Choose each runner's effort according to the delegation reference.
4. Give each candidate its own output location: a git worktree where possible, otherwise `/tmp/arena-<slug>/candidate-<n>/`. This follows the separate-before-serializing-shared-state principle.

## Phase B: Fan out

Start all candidates in one message, in the background. Give each the task, the path to the shared grounding, its own output path, and the instruction to produce the result and a short rationale that names the alternatives it considered and what it rejected.

If a candidate produces nothing, continue with the others and note the dropout.

## Phase C: Cross-judge

After all candidates finish, start one read-only judge on an other-vendor model. The judge is never from your own vendor. If no other vendor is available, skip the judge, pick the base alone in Phase D, and say so. The judge gets the rubric and the candidates by folder name, scores each criterion, and recommends a base with its reasons. It runs while you read the candidates in Phase D. Do not start it while candidates are still writing.

## Phase D: Pick a base

Read every candidate completely before you pick. Score each one against the rubric, one criterion at a time, not on overall feel. Compare your scores with the judge's when Phase C ran one. If you agree on the base, the pick is confirmed. If you disagree, one of you is biased or the rubric was unclear. Read both sets of reasons before you decide.

Pick the base that a future maintainer can extend most easily without breaking invariants. When two are close, prefer the cleaner boundary or the smaller API, according to the abstractions principle.

## Phase E: Graft

Go through each other candidate once more for parts worth adding to the base. This is usually one or two parts per candidate, not most of it. Add each part by hand, so that the result stays coherent under one model, according to the redesign-from-first-principles principle. Do not paste mechanically.

If the candidates agree on one shape, that is strong agreement. Note it and ship that shape without grafts. If they differ wildly, Phase A was not specific enough. Frame the task again and run the arena again. Do not average the differences.

## Phase F: Verify

Verify the combined result like any other output, according to the prove-it-works principle. If verification finds a problem that the arena missed, either Phase A was wrong, so frame and run again, or a candidate caught it and you missed the graft, so go back to Phase E. Do not hide it.

## Output

One combined result, with a short note next to it: the base and why, the judge's verdict or that Phase C skipped the judge, each graft and its source candidate, what you rejected and why, any agreement or dropouts, and the verification result.
