---
name: factory-implement
description: "Implement one understood Factory software change, add the smallest sufficient tests, run focused checks, account for the complete diff, and create the authorized local commit for independent assurance."
---

# Factory Implement

Produce a clean committed revision that implements the accepted behavior.
For large tasks, use coherent parts with shared constraints and a combined
final check. Keep one active implementation owner.

## Inputs

Require an aligned task contract, sufficient repository assessment, current
assurance record, approved behavioral paths and proof, repository, clean
starting worktree, and
edit, test, and commit authority. Require an approved plan-assurance result when
the current risk assessment requires it.

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
8. Commit coherent work after its focused checks pass. Return the exact final
   commit and a clean worktree.

Retry a failed operation only after a changed precondition or when the failure
is plausibly transient. Make at most two attempts for the same blocker.

## Outputs

Return:

- status: `complete`, `in-progress`, `needs-triage`, `needs-input`, or `blocked`
- exact base and committed revision, branch, and clean-worktree result
- updated assurance record with complete diff groups, proof results and
  revisions, uncovered behavior, exceptions, and residual risk
- a short behavior summary and any scope or risk decision needed

## Side effects

Modify approved local files, run local checks, and create scoped commits. Do
not amend, rebase, change unrelated user work, approve your implementation,
or write to remote systems.

## Failure results

Return `in-progress` after a bounded part when accepted behavior remains.
Preserve the complete task requirements and use planned evidence for remaining
work. Only `complete` requests final independent review. Return `needs-triage`
when a new code or dependency fact needs investigation. Preserve unaffected
work and evidence. Return `needs-input` for missing authority or a material
decision. Return
`blocked` for an inaccessible required dependency or proof. Leave no commit
when required focused checks fail.
