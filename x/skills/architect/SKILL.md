---
name: architect
description: Sketch types, signatures, and module structure before code, compare distinct designs, and choose one before implementation. Use for code that crosses a function boundary, or when going straight to code would lock in the wrong shape.
---

# Architect

Sketch the types, the function signatures, and the module boundaries, with `not implemented` bodies and pseudocode. Compare designs from several models, choose one, and then write the code against the chosen sketch.

Add one todo item for each phase: Ground, Sketch, Agree, Implement, Scrap.

## Phase A: Ground

Learn every system that the new code touches. Trace the affected code, and write a short explanation of how each part works. Naming a file is not grounding. If the design changes ownership or layering, use the **why** skill on the current shape, so that its reasons become constraints and not guesses.

Skip this phase only for new code with no surrounding system.

## Phase B: Sketch

Run the **arena** skill with the design-sketch task and the Phase A results. Give each runner [references/runner-prompt.md](references/runner-prompt.md) as its prompt.

- Build at least two designs that differ in their whole shape, not in one detail, even when the first looks good enough. This is the exhaust-the-design-space principle.
- Check every design against [references/design-red-flags.md](references/design-red-flags.md). Assume that the next contributor is an agent that sees only the files it opened, copies the nearest example, and takes the shortest path that compiles. Prefer the design where a change that looks right in one file is right for the whole repo.
- Prefer the design that hides more complexity behind a smaller and simpler public interface.

Arena returns one combined design. Its decision fills the "Synthesis decision" section of the rationale.

## Phase C: Agree

By default, continue to implementation with the combined design. Stop for the user's approval only when the user asks for it, for example "stop and show me before you implement".

The sketch can ship as its own commit, as the scaffold-first part of the foundational-thinking principle. To challenge the design before you implement it, run the **interrogate** skill on the sketch.

If the user disagrees with the shape, treat that as new Phase A evidence. Ground again and run Phase B again before you write more code.

## Phase D: Implement

Replace each `not implemented` body with code, and each pseudocode block with logic. The sketch is the contract. Report each deviation from it. Do not absorb it quietly. If a function needs a parameter that the sketch did not have, decide whether the sketch was wrong, a requirement was missed, or the implementation does too much.

## Phase E: Scrap

If the implementation keeps fighting the sketch, throw the sketch away, according to the redesign-from-first-principles and fix-root-causes principles. The signal is a pattern, not one case:

- The same kind of workaround appears again and again in unrelated code.
- Several unrelated edge cases each need their own special branch.
- Types need escape hatches, such as `any`, casts, or optional fields that are always set, to compile.
- You need a lock, but the sketch said the state was not shared.
- Callers must know the abstraction's internal rules to use it.
- Two or more Phase D deviations have the same shape.

A few edge cases do not condemn a design. Complex data is not a complex design.

To scrap:

1. Trace what you built.
2. Design again as if the new constraints were known from the start.
3. Remove before you add, according to the subtract-before-you-add principle. The new sketch is smaller than the old one before it grows.
4. Go back to Phase B.

## Output

Write the caller's usage first, and derive the type sketch from it. For a small change, write one file with the new types and signatures. For larger work, write a module map and the type definitions. Write the rationale next to the sketch with [references/rationale-template.md](references/rationale-template.md). Save both in the task's context folder.
