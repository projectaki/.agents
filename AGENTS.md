# Coding guide

Domain driven design (DDD)
Vertical slices, where slices encapsulate domain models, validation, errors, interfaces, services, utils for a slice.
Each slice has interfaces which can be used by other slices
Each slice also has implementations for each interface, which can be provided at application boundaries.
Follow the SOLID principles. Always prioartize collocating things that change together, by designing and organizing code in a way to support extention and not modification.
Always prefer composition over inheritance.
Avoid deep nesting, prefer guard clauses to favor readability.
Always think about error handling, and ensure that we handle all paths.
Always treat observability as a first class candidate. From the very begining think about tracing, logging.
Always aim to write the simplest and most readable code.
Avoid simple abstractions. Things that can be inlined should be inlined. Every abstraction we pay a price of indirection. Abstractions can make sense for larger complex actions.

Always write unit tests for static/pure functions.
When designing the system always think about integration tests, that we will need.