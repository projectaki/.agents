---
name: factory-implement
description: "Implement one triaged Factory software change, add the smallest sufficient tests, run focused checks, account for the complete diff, and create the authorized local commit for independent assurance."
---

# Factory Implement

## Purpose

Produce one clean committed revision that implements the accepted task.

## Inputs

Require an aligned task contract, ready triage result, current assurance record,
approved behavioral paths and proof, repository, clean starting worktree, and
edit, test, and commit authority. Require an approved plan-assurance result when
triage marked it necessary.

## Operation

1. Confirm the task revision, authority, Git head, branch, and clean worktree.
2. Implement only the accepted scope with repository patterns.
3. For a deterministic bug, add the permanent regression test, confirm that it
   fails for the reported behavior, apply the fix, and rerun it. Use separate
   reproduction only when triage requires it.
4. For a feature, add the smallest acceptance tests that prove the new behavior
   and relevant failure paths. Confirm a preimplementation failure when that
   signal is meaningful and practical.
5. Run the smallest focused checks mapped to the accepted paths and risks.
6. Inspect the complete diff. Map every change group to an accepted path or an
   explicit non-behavioral reason.
7. Stop for scope growth, a higher risk class, a contract-invalidating finding,
   or inaccessible required proof.
8. Create one local commit after focused checks pass. Return the exact commit
   and a clean worktree.

Retry a failed operation only after a changed precondition or when the failure
is plausibly transient. Make at most two attempts for the same blocker.

## Outputs

Return:

- status: `complete`, `needs-input`, or `blocked`
- exact base and committed revision, branch, and clean-worktree result
- changed behavior, files, and complete diff groups
- tests and checks with results and covered revision
- updated paths, risks, evidence, exceptions, and residual risk
- skipped or inaccessible required checks
- scope or risk changes and the exact decision they require

## Side effects

Modify approved local files, run local checks, and create one local commit. Do
not push, publish, amend, rebase, or change unrelated user work.

## Failure results

Return `needs-input` for missing authority or a material decision. Return
`blocked` for an inaccessible required dependency or proof. Leave no commit
when required focused checks fail.

## Non-goals

Do not expand scope, approve your own implementation, push, publish, merge, or
release.
