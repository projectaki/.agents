---
name: architect
description: Sketch types, signatures, and module structure before code, compare distinct designs, and choose one before implementation. Use for code that crosses a function boundary, or when going straight to code would lock in the wrong shape.
---

# Architect

Before you write code, trace every system that the change touches. Then sketch two different shapes for the change: the types, the signatures, and the module boundaries. Choose the shape where each piece of state has one owner, each task has one way to do it, and callers need to know the least. If the same workaround appears again and again, design the shape again. Do not add more patches.

For a large or contested design, run the **arena** skill. Do not sketch it alone.
