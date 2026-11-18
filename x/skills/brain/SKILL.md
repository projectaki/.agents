---
name: brain
description: My engineering principles. Read before you make a design or code decision, and read each principle that applies.
---

# Brain

Each principle is a file in `principles/` next to this file. Read every principle whose condition applies to the current decision.

## Engineering

- [Role and goals](principles/goals.md): read at the start of each task. It gives the role, the goals, and the anti-goals.
- [Experience first](principles/experience-first.md): read when you make a product, UX, or scope tradeoff.
- [Decision framework](principles/decision-framework.md): read when two or more implementations are possible.
- [Foundational thinking](principles/foundational-thinking.md): read before you start new code. Choose the data structures first, then the scaffold.
- [Exhaust the design space](principles/exhaust-the-design-space.md): read when a design decision has no example in the codebase. Build 2 or 3 versions in code and compare them.
- [Redesign from first principles](principles/redesign-from-first-principles.md): read when a new requirement does not fit the existing design.
- [Subtract before you add](principles/subtract-before-you-add.md): read before you add code to an area that is already complex.
- [Outcome-oriented execution](principles/outcome-oriented-execution.md): read when you plan a rewrite, a migration, or a change to an internal API.
- [Build the lever](principles/build-the-lever.md): read when a task is repetitive or large enough that a script or tool can do it.
- [Model the domain](principles/model-the-domain.md): read when you write business rules, or when conditionals about one concept appear in several places.
- [SOLID](principles/solid.md): read when you decide what a module, class, or function is responsible for.
- [Framework and feature boundaries](principles/framework-and-feature-boundaries.md): read when shared code must behave differently for each feature or kind.
- [Composition](principles/composition.md): read when you consider inheritance.
- [Abstractions](principles/abstractions.md): read before you add a function, class, module, or layer, or before you repeat a decision.
- [Readability](principles/readability.md): read when you write control flow or a code comment.
- [Fix root causes](principles/fix-root-causes.md): read when you debug.
- [Attack the premise](principles/attack-the-premise.md): read after two fixes for the same problem fail.
- [Boundary discipline](principles/boundary-discipline.md): read when data enters or leaves the system, or when you add validation or error handling.
- [Encode lessons in structure](principles/encode-lessons-in-structure.md): read when the same problem or review correction comes back.
- [Type system discipline](principles/type-system-discipline.md): read when you define types, or when a value can be in an impossible state.
- [Error handling](principles/error-handling.md): read when code can fail.
- [Make operations idempotent](principles/make-operations-idempotent.md): read when an operation changes state and can run again or stop in the middle.
- [Separate before serializing shared state](principles/separate-before-serializing-shared-state.md): read when two or more actors can write the same state at the same time.
- [Observability](principles/observability.md): read when you design a system or a code path that can fail in production.
- [Prove it works](principles/prove-it-works.md): read before you say that a task is done.
- [Explain the number](principles/explain-the-number.md): read before you measure, and before you trust, report, or act on a number that you measured.
- [Sequence verifiable units](principles/sequence-verifiable-units.md): read when work has more than one step, or before you open a pull request.
- [Testing](principles/testing.md): read when you write or change tests, or design code that needs tests.
