# Model the Domain

Model the business domain explicitly.

Business rules belong inside the domain.

Avoid leaking infrastructure concerns into domain code.

## Encode the domain in a structure

Put the real domain into a data structure. Do not spread it across conditionals. A structure that matches the domain makes invalid states impossible and removes branches. Choosing it while you write the code costs little. Adding it later becomes a refactor that people postpone.

Use structures such as these:

- A state machine, not scattered booleans, phases, or lifecycle checks.
- A typed model, not loose parameters or repeated assumptions about data shape.
- A map, registry, lookup table, or discriminated union, not branches spread across files.
- A reducer or a command and event model, not unplanned state changes.
- A module that owns one area of domain knowledge, not modules named after steps such as load, validate, transform, and save. The order of execution does not decide ownership.
- A small module boundary that collects repeated behavior, ownership, or invariants.
- A queue, cache, index, graph, tree, or normalized collection when the access pattern needs it.
- Any other structure that fits. When none fits, find what the code must never allow and how the code reads the data. Then choose the structure that encodes exactly that.

Do not force an abstraction. If the current code is clear, local, and unlikely to grow, keep it simple. Do not trust an abstraction that adds indirection but removes no branches, duplicate rules, invalid states, or lifecycle risk.

## Signs that the model is missing

- A new feature adds one more branch to an existing if/else chain.
- A second boolean must stay in sync with the first.
- Modules named after steps repeat the same domain rules.
