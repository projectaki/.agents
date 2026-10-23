---
name: ensure-quality
description: Check all proposed or implemented changes against every applicable AGENTS.md principle and resolve violations.
---

Read all applicable AGENTS.md files. Treat their current instructions as authoritative over this checklist.
Review the complete task scope, including proposed changes, committed changes, and uncommitted files.
Check every principle against every relevant change. Inspect affected callers, dependencies, and tests.

## Principles

- Correctness: Meet the requirements and preserve required behavior.
- Maintainability: Make the work easy to understand, test, debug, modify, extend, and deploy safely.
- Simplicity: Choose the smallest sufficient solution. Avoid speculative flexibility, unnecessary indirection, heavyweight frameworks, and disproportionate dependencies.
- Interfaces and naming: Keep public interfaces small and explicit. Use descriptive names.
- Domain design: Model business concepts explicitly. Keep business rules separate from infrastructure.
- Responsibility: Give each module one clear responsibility. Group things that change together.
- Dependencies: Make policy depend on abstractions rather than infrastructure details.
- Extension: Support required variation without modifying stable framework logic. Do not add abstractions for hypothetical variation.
- Framework boundaries: Keep feature names, imports, and branches out of framework code. Define variation interfaces in the framework. Implement them beside each feature. Register them by key outside the framework. Adding a kind must need only feature files and one registration line.
- Composition: Prefer composition. Justify any inheritance.
- Readability: Use explicit behavior, guard clauses, early returns, and shallow control flow. Avoid cleverness without measurable benefit.
- Comments: First clarify names, structure, types, or tests. Keep only short, necessary explanations of constraints or non-obvious reasons. Remove stale comments. Put broad reasoning in durable documentation.
- Errors: Cover every code path. Address validation, expected and unexpected failures, retries, propagation, and recovery. Make errors meaningful.
- Observability: Assess structured logs, traces, metrics, correlation identifiers, and error context during design. Implement what the behavior needs.
- Abstractions: Require reduced complexity or a meaningful concept. Avoid trivial wrappers, unnecessary single-use abstractions, and abstractions that obscure behavior.
- Unit tests: Cover pure functions, deterministic business logic, validation, and utilities. Keep tests isolated, deterministic, and fast.
- Integration tests: Keep business logic separate from infrastructure. Make integration testing straightforward.
- Decisions: Prefer simplicity, low cognitive load, fewer dependencies, explicit behavior, testability, extensibility, and low maintenance cost, in that order.
- File search: Follow the applicable file-search instructions.
- Communication: Use Simplified Technical English, short active sentences, and one idea per sentence. Explain identifiers each time. Define new terms. Avoid invented labels, metaphors, and unexplained jargon.
- External text: Write in my voice. Use first-person singular for my actions and decisions. Keep neutral facts neutral. Do not invent collective authorship or impersonate me in messages addressed to me.
- Documents: Describe the current state. Replace obsolete content. Keep documents self-contained. Include necessary reasoning. Preserve history only when requested or needed to explain a constraint. Reread each complete edited document.

## Enforcement

- Check additional rules from applicable AGENTS.md files too.
- Fix violations within the authorized scope. Recheck affected principles after each fix.
- Obtain my explicit approval before exceptions, workarounds, or technical debt.
- Investigate uncertain designs with small, reversible experiments. Obtain approval if material uncertainty remains.
- Explain any approval request with the rule, evidence, uncertainty, scope, alternatives, risks, costs, validation, recovery, and removal condition.
- Continue independent safe work while awaiting approval. Never infer approval from silence or urgency.
- Document approved exceptions and their limits. Seek new approval when those limits change.
- Run relevant checks. Treat missing evidence and failed checks as unresolved.
- Report each principle as met, unmet, unverified, not applicable, or covered by an approved exception. Give brief evidence or a reason for each result.
- Distinguish proposed compliance from verified implementation. Do not declare full compliance while applicable requirements remain unresolved.
