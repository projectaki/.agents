# Outcome-Oriented Execution

Aim for the planned end state. Do not try to keep every intermediate step fully working.

When every intermediate step must stay stable, you write temporary compatibility code. That code often stays and becomes debt. Go directly to the target design and prove correctness at defined check points.

- A correct end state is more important than stable intermediate steps.
- Intermediate breakage is acceptable when it is planned, limited, and reversible.

Limits:

- Use this only for planned rewrites and migrations that have clear phases.
- State in advance where temporary breakage is acceptable.
- During the migration, keep the important checks running for the areas that you change.
- At the end, run all static checks and all runtime checks.
- Breakage is acceptable only inside a branch or an unmerged stack. Each merged pull request must build, pass its tests, and be safe to deploy.

## Replace internal APIs in one step

When a new internal API replaces an old one, move all callers to the new API and delete the old API in the same piece of work. Do not keep a compatibility layer.

- Update the tests so they check the new contract. Delete tests that only protect implementation details from before the change.

Apply this only when all of these are true:

- No external users depend on backward compatibility.
- The project can handle a coordinated breaking change.
- The new API is part of a simplification or a refactor.
