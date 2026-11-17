# Architect runner prompt

The lead gives this file to each runner in Phase B, together with the task, the Phase A results, the runner's own working directory, and the path for its output. Each runner works independently of the others.

You build one candidate design. Read the **architect** skill first, because that is the workflow you are in. Write a design package: a type sketch, function signatures, a module map, and a rationale with [rationale-template.md](rationale-template.md).

The lead compares the candidates on these points:

- **The caller's usage first.** Write the README-style usage and two or three real call sites before the types. Then derive the type sketch from them. The usage is the spec. When the two disagree, change the sketch to match the usage.
- **Data structures first,** according to the foundational-thinking principle. Trace each main access pattern through the structure. If the answer is "we'll add a map, an index, or a cache later", the structure is wrong.
- **Interface depth.** Prefer a simple interface that moves complexity into the callee, even when the implementation gets harder. Keep transport and wire types out of the public API, according to the boundary-discipline principle.
- **Shared state.** If two actors can write the same state, apply the separate-before-serializing-shared-state principle.
- **Visible boundaries.** Use `not implemented` errors for bodies, `// TODO` pseudocode for the hard logic, and doc comments for intent and invariants. A reader can follow the data from input to output from the types and signatures alone.
- **Invariants in types,** according to the type-system-discipline and encode-lessons-in-structure principles.
- **Validate at the boundary and trust types inside,** according to the boundary-discipline principle. Keep business logic in pure functions.
- **One source of truth for each invariant.** Derive values. Do not sync them.
- **Idempotent state changes,** according to the make-operations-idempotent principle.
- **Short call chains.** If you need more than three files to follow the flow, flatten it, according to the abstractions and readability principles.

Each runner uses a different model. Build the best design your model can. Do not hedge toward a safe middle. The differences between candidates are what the lead uses to choose.
