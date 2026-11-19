# Model the Domain

Model the business domain explicitly.

Business rules belong inside the domain.

Avoid leaking infrastructure concerns into domain code.

## Encode the domain in a structure

Put the domain into a data structure. Do not spread it across conditionals. The right structure makes invalid states impossible and removes branches.

Use a state machine, not scattered booleans or phase checks. Use a typed model, not loose parameters. Use a map, a registry, or a discriminated union, not branches spread across files. Use a reducer, not unplanned state changes. Use an index, a queue, or a normalized collection when the access pattern needs it.

Do not force it. Keep simple code when the shape is clear, local, and unlikely to grow. Do not trust an abstraction that adds indirection but removes no branches or invalid states.

You skipped this when a feature adds one more branch to an if/else chain, or when a second boolean must stay in sync with the first.
