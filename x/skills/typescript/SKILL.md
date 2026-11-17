---
name: typescript
description: TypeScript best practices, project structure, and Effect. Use when you read, edit, or create a .ts or .tsx file, or start a TypeScript project.
paths: ["**/*.ts", "**/*.tsx"]
---

# TypeScript

First, read the type-system-discipline and boundary-discipline principles in the **brain** skill.

## Rules

| Rule | Summary |
|------|---------|
| Discriminated unions | Model variants with a `kind` literal discriminant so impossible states can't be represented. No optional-field bags. |
| Branded types | Brand primitives with `& { readonly __brand: "X" }` so they can't be mixed up. Validate once at the boundary. A brand comes from a verifying type guard (`input is AgentId`), never from `as`. |
| Constructive modeling | Build the shape so the illegal value can't be constructed. `[T, ...T[]]` for non-empty, `[T, T][]` for even length, `start` plus `duration` for a range. Not a runtime guard, not a wish for refinement types. |
| Simplest total type | Keep `T[]` while every operation on it stays total. Strengthen to `NonEmpty<T>` only where the loose type forces `!`, a cast, or a "should never happen" throw. |
| `unknown` over `any` | External data is `unknown`. |
| Schemas before guards | Before hand-writing a property-by-property type guard, use the repository's runtime schema library and infer the type from the schema, such as `z.infer` or Effect `Schema`. |
| No `as` casts | Every `as` is a runtime crash waiting. Cast only after validation. |
| Narrowing hierarchy | Discriminant switch > `in` operator > `typeof`/`instanceof` > user-defined type guard > `as`. |
| Type guards | Must verify the claim. A lying guard is worse than `as` because the bug hides behind a name that says it's safe. Name them `isX` or `hasX`. |
| Exhaustiveness | Inline `const _exhaustive: never = x;` in default arms so the compiler errors when a new variant is added. |
| `satisfies` over `as` | Validates the value without widening literal types. |
| Boundary validation | Parse where data crosses in, into a named domain type. `Record<string, unknown>` (however spelled) stops at that parse. Trust types inside. |
| Schema-derived types | Reach for `Pick`/`Omit`/`Parameters`/`ReturnType`/`Awaited`/`typeof` before declaring a new interface. |
| Object args | Pass objects, not positional, so argument order is self-documenting. Skip on hot paths (per-frame render, tokenizers, parsers). |
| Real tests | Don't mock what you can run. Prefer the framework's real test primitives with leak/disposable checks, and verify UI in a running build. Mock only what you can't run locally. |
| Structured telemetry | Prefer structured logger diagnostics with enough context to debug from an id. No `console.log` in shipped code. |

Examples for each rule: [references/patterns.md](references/patterns.md).

## Effect

Use Effect v4 as the standard library in every TypeScript project, unless there is a strong reason not to. Use Effect for effects, dependency injection, configuration, errors, concurrency, resources, scheduling, retries, streams, queues, logging, and observability.

- Do not mix async styles. Use `Promise` only at external boundaries.
- Design APIs so that they compose with Effect.
- Do not guess Effect patterns. Before you write Effect code, run `effect-solutions list`, then `effect-solutions show <topic>...` for each topic that applies. Topics: quick-start, project-setup, tsconfig, basics, services-and-layers, data-modeling, error-handling, config, testing, cli.
- For APIs, examples, and implementation details that the guides do not cover, search the Effect source at `~/.local/share/effect-solutions/effect`.

## Project structure

Read [references/project-structure.md](references/project-structure.md) before you start a TypeScript project, add a package, or add or change a vertical slice.
