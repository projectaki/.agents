---
name: arena
description: Run several candidates on the same task in parallel, pick the best as a base, and add the strongest parts of the others to it. Use for a design or code bake-off, or when one attempt at a non-trivial result would lock in the wrong shape.
---

# Arena

Add one todo item for each phase: Frame, Fan out, Cross-judge, Pick, Graft, Verify.

## Phase A: Frame

Every candidate gets the same prompt, so the prompt is the contract.

1. State the result that each candidate produces.
2. Write a rubric: 3 to 6 concrete criteria that define success for this task. Take each criterion from the real system's contract, such as its docs or its real output. Do not guess, because the judge applies each criterion literally. Only you and the judge see the rubric. Candidates see only the task.
3. Choose the runners. Use native subagents, each on a different model. By default, use the two strongest models that your harness offers. In Claude Code, these are `opus` and `sonnet`. Add a runner from another provider through its CLI, according to the delegation reference, only when the user asks for it or the result is hard to change later. It is slower, but it finds what your provider's models miss. Add runners when the arena covers several design directions. Use the same model twice only when the work depends on volume more than on judgment.
4. Give each candidate its own output location: a git worktree when it edits code, or its own folder in the task's context folder. This follows the separate-before-serializing-shared-state principle.

## Phase B: Fan out

Start all candidates in one message, as background subagents. Give each the task, the path to the shared grounding, its own output path, and this instruction: write the result and a short rationale file that names the alternatives it considered and what it rejected, and reply with only a few lines. The files are the result, so the replies stay short.

If a candidate produces nothing, continue with the others and note the dropout.

## Phase C: Cross-judge

After all candidates finish, start one read-only judge as a native subagent on your strongest model. In Claude Code, this is `opus`. Blind it: name each candidate only by its folder, and never tell the judge which model wrote it, so it cannot favor its own model. The judge gets the rubric and the candidates by path, scores each criterion with a file and line as evidence, and recommends a base with its reasons. It runs while you read the candidates in Phase D.

## Phase D: Pick a base

Read every candidate completely before you pick. Score each one against the rubric, one criterion at a time, not on overall feel. Compare your scores with the judge's. If you agree on the base, the pick is confirmed. If you disagree, one of you is biased or the rubric was unclear. Read both sets of reasons before you decide.

Pick the base that a future maintainer can extend most easily without breaking invariants. When two are close, prefer the cleaner boundary or the smaller API, according to the abstractions principle.

## Phase E: Graft

Go through each other candidate once more for parts worth adding to the base. This is usually one or two parts per candidate, not most of it. Add each part by hand, so that the result stays coherent under one model, according to the redesign-from-first-principles principle. Do not paste mechanically.

If the candidates agree on one shape, that is strong evidence. Say so, and ship that shape without grafts. If they differ wildly, Phase A was not specific enough. Frame the task again and run the arena again. Do not average the differences.

## Phase F: Verify

Verify the combined result like any other output, according to the prove-it-works principle. If verification finds a problem that the arena missed, either Phase A was wrong, so frame and run again, or a candidate caught it and you missed the graft, so go back to Phase E. Do not hide it.

## Output

One combined result, with a short note next to it: the base and why, the judge's model and verdict, each graft and its source candidate, what you rejected and why, any agreement or dropouts, and the verification result.
