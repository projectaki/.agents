---
name: x-ensure-quality
description: Investigate proposed or implemented changes against AGENTS.md principles and module design checks. Report findings and proposed improvements without making changes.
---

Read all applicable AGENTS.md files. Treat their current instructions as authoritative over this checklist.
Review the complete task scope, including proposed changes, committed changes, and uncommitted files.
Check every principle against every relevant change. Inspect affected callers, dependencies, and tests.
Investigate and plan only. Do not change files or repository state. Present findings and proposed work in chat. I decide what to implement and when.
Treat the principles below as review criteria, not instructions to make changes.

## Principles

- Correctness: Meet the requirements. Distinguish intended behavior changes from structural refactoring. Check that refactoring preserves observable behavior.
- Maintainability: Make the work easy to understand, test, debug, modify, extend, and deploy safely.
- Simplicity: Choose the smallest sufficient solution. Avoid speculative flexibility, unnecessary indirection, heavyweight frameworks, and disproportionate dependencies.
- Interfaces and naming: Keep public interfaces small and explicit. Check that callers depend only on the capabilities and data they need. Use descriptive names.
- Compatible implementations: Check that interchangeable implementations preserve the same input requirements, results, errors, and state guarantees.
- Domain design: Model business concepts explicitly. Keep business rules separate from infrastructure. Check that construction and state changes enforce required business conditions without relying on each caller to remember them.
- Responsibility: Give each module one clear responsibility. Group things that change together.
- Dependencies: Make policy depend on abstractions rather than infrastructure details. Identify framework types, storage formats, and transport details that unnecessarily enter business-facing interfaces.
- Extension: Support required variation without modifying stable framework logic. Do not add abstractions for hypothetical variation.
- Framework boundaries: Keep feature names, imports, and branches out of framework code. Define variation interfaces in the framework. Implement them beside each feature. Register them by key outside the framework. Adding a kind must need only feature files and one registration line.
- Composition: Prefer composition. Justify any inheritance.
- Readability: Use explicit behavior, guard clauses, early returns, and shallow control flow. Avoid cleverness without measurable benefit.
- Comments: First clarify names, structure, types, or tests. Keep only short, necessary explanations of constraints or non-obvious reasons. Remove stale comments. Put broad reasoning in durable documentation.
- Errors: Cover every code path. Address validation, expected and unexpected failures, retries, propagation, and recovery. Make errors meaningful.
- State and effects: Check for hidden mutation, shared mutable state, unexpected external effects, and undocumented call-order requirements.
- Observability: Assess structured logs, traces, metrics, correlation identifiers, and error context during design. Implement what the behavior needs.
- Abstractions: Require reduced complexity or a meaningful concept. Avoid trivial wrappers, unnecessary single-use abstractions, and abstractions that obscure behavior.
- Duplicated knowledge: Identify duplicated business rules that must stay consistent. Do not combine unrelated behavior merely because its code looks similar.
- Decisions: Prefer simplicity, low cognitive load, fewer dependencies, explicit behavior, testability, extensibility, and low maintenance cost, in that order.
- File search: Follow the applicable file-search instructions.
- Communication: Use Simplified Technical English, short active sentences, and one idea per sentence. Explain identifiers each time. Define new terms. Avoid invented labels, metaphors, and unexplained jargon.
- External text: Write in my voice. Use first-person singular for my actions and decisions. Keep neutral facts neutral. Do not invent collective authorship or impersonate me in messages addressed to me.
- Documents: Describe the current state. Replace obsolete content. Keep documents self-contained. Include necessary reasoning. Preserve history only when requested or needed to explain a constraint. Reread each complete edited document.

## Module design checks

- Read relevant domain documentation and architecture decisions when present. Check names and responsibilities against them.
- Check the full caller contract, including ordering, configuration, constraints, state ownership, and errors.
- Check whether each module hides useful complexity. Question wrappers that leave callers responsible for the same details.
- Check whether one business rule requires knowledge or changes across several modules. Propose consolidation only when it reduces complexity without mixing responsibilities.
- Consider established design patterns when they solve a concrete problem. Explain the benefit, added complexity, and simplest sufficient alternative. Use language features where possible.
- Consider Strategy for interchangeable behavior, Adapter for incompatible interfaces, and Facade when callers must coordinate complex internals.
- Consider Decorator for independently combined behaviors and Chain of Responsibility for ordered handlers. Check execution order and failure propagation.
- Consider Command for queued, delayed, or undoable operations and Observer for independent event subscribers. Check delivery expectations, ownership, and cleanup.
- Check that internal details stay private rather than becoming public only to support tests.

## Testing checks

- Check unit coverage of pure functions, deterministic business logic, validation, and utilities. Tests must be isolated, deterministic, and fast.
- Check that business logic is separate from infrastructure and integration testing is straightforward.
- Check observable behavior through module interfaces, including interactions and isolated logic. Assertions must detect incorrect outcomes and important failure cases.
- For stateful workflows, check allowed and rejected transitions, transition conditions, resulting effects, and important event sequences.
- Check that test substitutes represent relevant production behavior.
- Preserve useful unit coverage in proposed refactors. Do not treat coverage percentages as proof of correctness.

## Conditional checks

- Stateful workflows: Prefer an explicit state machine when lifecycle states, transition rules, or event order govern behavior. Check defined states, triggering events, allowed transitions, transition conditions, and effects. Identify contradictory state flags and transitions that bypass the rules. Use the simplest sufficient representation; a state machine does not require a framework.
- Persistent or concurrent changes: Check transaction boundaries, partial updates, conflicting writes, and lost updates.
- Remote calls and background work: Check timeouts, bounded retries, duplicate processing, cancellation, and partial failure.
- Resource ownership: Check that allocated resources have clear owners and are released on success, failure, and cancellation.
- Existing consumers and data: Check compatibility with deployed callers, stored data, and queued messages. Identify necessary migration steps.
- Workload and growth: Identify repeated remote calls, unbounded reads, and processing that grows poorly with realistic input sizes. Require evidence before recommending optimization.
- Protected operations and untrusted input: Check authorization, resource ownership, and input validation at the boundary that enforces access.

## Findings and plan

- Check additional rules from applicable AGENTS.md files too.
- Apply the checks to the current changes and affected code. Use conditional checks only where relevant. Report unrelated improvements separately.
- Treat design heuristics as investigation prompts. Report a design problem only when you can explain its concrete impact and supporting evidence. Distinguish defects, requirement violations, and optional improvements.
- Support each finding with file references and propose the simplest improvement.
- Identify exceptions, workarounds, technical debt, and uncertain designs that would require my approval. Check existing approvals and their limits.
- For such proposals, explain the rule, uncertainty, alternatives, risks, maintenance and testing costs, validation, recovery, and any removal condition.
- Inspect existing tests and available check results. Propose missing validation or small, reversible experiments without performing them. Treat missing evidence and failed checks as unresolved.
- Report each principle as met, unmet, unverified, not applicable, or covered by an approved exception. Give brief evidence or a reason for each result.
- Distinguish proposed compliance from verified implementation. Do not declare full compliance while applicable requirements remain unresolved.
