# Sequence Work into Verifiable Units

Do the work as a sequence of small units. Each unit ends in a state that you can check. Do not start the next unit until the current unit passes its check.

In a sweep, a migration, or a run of similar edits, each unit goes from a known good state, through one change, to a check, and only then to the next unit. Run the check for each unit even when a script makes the edits.

Deliver in the order that proves the work: the failing test first, then the fix. Removal comes before restructuring, and a measurement of the starting point comes before the change. Each commit works on its own. When a fix belongs in the commit that you just made, amend that commit. When the fix stands on its own, make a new commit.

## Pull request size

- Aim for about 100 changed lines or fewer in a pull request that changes behavior. Count additions and deletions, including tests and hand-written supporting changes. For one cohesive change, 100 to 300 lines is acceptable. Above 300 lines, look for a split that makes sense. Keep changes together when a split makes the behavior harder to verify. Keep the tests that prove a change in the same pull request as the behavior that they cover.
- Group generated output, documentation-only updates, and mechanical edits by purpose. Give each group its own pull request when it can be verified and merged safely on its own or with the pull requests before it. These pull requests can be larger when the reviewer can easily verify the generator, the documentation scope, or the mechanical operation. Review refactors whose behavior is difficult to verify with the usual care.
- When generated output must land with its source change, keep both in one pull request. Put the generated output in a separate commit, and report its line count separately from the lines that count toward the target.
