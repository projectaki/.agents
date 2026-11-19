# Readability

Prefer:

- guard clauses
- early returns
- shallow control flow
- explicit behavior
- self explaining code without code comments

Avoid deep nesting whenever possible.

## Reader load

Maintainability is the work a reader must do to understand code. Measure it in two independent ways:

- Layers to trace: the steps of indirection between a question and its answer.
- State to hold: the hidden or changeable context the reader must keep in mind.

A flat file with 50 global variables can be as hard to read as a stack of 6 adapters. Reduce both.

- Each layer must change the abstraction. A layer that repeats the methods and arguments of the layer below adds work and gives nothing. Remove it.
- An interface must hide real complexity. A broad interface that hides little makes the reader learn both the interface and the implementation.
- Keep state as narrow as possible. Prefer pure functions that return values to functions that change state. Prefer local variables to fields, fields to module state, and module state to globals. Calculate values from their source. Do not keep copies in sync.
- State each invariant once, at the boundary, and not again in every caller.
- Before you add a layer or state, check that it removes at least as much reader work somewhere else.

Test: a new reader must answer "Where does X come from?" and "What can change X?" in less than 30 seconds. If they cannot, remove layers or state.

## Code Comments

Treat a code comment as a last resort. Add one only when critical information
must remain beside the code and cannot be made clear through naming, structure,
types, or tests.

- Keep comments short. Do not write large paragraphs or detailed narratives.
- Explain a necessary constraint, workaround, or non-obvious reason. Do not
  restate what the code does.
- Put broad reasoning, implementation history, and review context in the pull
  request description or durable documentation instead.
- Do not add a comment only because information was useful during development.
- Remove a comment when the code no longer needs it or when the information is
  no longer accurate.
- Before adding a comment, first try to make the code self-explanatory.
