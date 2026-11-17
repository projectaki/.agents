# Sequence Work into Verifiable Units

Do the work as a sequence of small units. Each unit ends in a state that you can check. Do not start the next unit until the current unit passes its check.

A break that you find in the unit that caused it is easy to locate. A break that you find after a batch is hidden among other changes, and you have already built more on a broken base.

## While you work

In a sweep, a migration, or a run of similar edits, check each change before you start the next one. Each unit goes from a known good state, through one change, to a check, and only then to the next unit. First rebase onto a clean main branch, so that each check compares against the real starting point. When a script makes the edits, the check for each unit costs almost nothing. Run it anyway.

## When you deliver

Order commits and pull requests so that the order proves the work. The standard order is the failing test first, then the fix. Other orders are removal before restructuring, a measurement of the starting point before the change, and the scaffold before the feature. Each commit works on its own, and the sequence reads as an argument.

## Pull request size

- Aim for about 100 changed lines or fewer in a pull request that changes behavior. Count additions and deletions, including tests and hand-written supporting changes. For one cohesive change, 100 to 300 lines is acceptable. Above 300 lines, look for a split that makes sense. Keep changes together when a split makes the behavior harder to verify. Keep the tests that prove a change in the same pull request as the behavior that they cover.
- Group generated output, documentation-only updates, and mechanical edits by purpose. Give each group its own pull request when it can be verified and merged safely on its own or with the pull requests before it. These pull requests can be larger when the reviewer can easily verify the generator, the documentation scope, or the mechanical operation. Review refactors whose behavior is difficult to verify with the usual care.
- When generated output must land with its source change, keep both in one pull request. Put the generated output in a separate commit, and report its line count separately from the lines that count toward the target.

Keep each check real, according to [Prove it works](prove-it-works.md). Make each check cheap, according to [Build the lever](build-the-lever.md).
