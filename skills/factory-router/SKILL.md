---
name: factory-router
description: "Use only when the human explicitly asks to route a factory task. Read the current thread, supplied context, and all available skill metadata; choose the single next factory lifecycle stage and return it with one brief explanation without performing the stage."
---

# Factory Router

Choose the next top-level lifecycle. Do not perform lifecycle work.

## Workflow

1. Read the complete thread and supplied context.
2. Read the `name` and `description` metadata for every skill available in the
   runtime catalog and configured skill roots. Treat current metadata as the
   source of truth; do not rely on remembered skill behavior.
3. Choose from `factory-context`, `factory-replicate`, `factory-plan`,
   `factory-implement`, `factory-review`, `factory-verify`, `factory-learn`, or
   `complete`.
4. Select the earliest unmet lifecycle outcome required by the current state.
   Skip outcomes already established, route invalidated work back to the stage
   that must replace it, and resolve explicit uncertainty before advancing.

Use other skill metadata to understand available supporting capabilities and
which work a lifecycle performs internally; supporting skills are not router
destinations. Return `complete` only when no lifecycle work remains. Do not
infer completion from effort or unsupported claims.

## Output

Return exactly two lines:

```text
stage: <stage-name>
reason: <one short sentence grounded in the context and skill metadata>
```
