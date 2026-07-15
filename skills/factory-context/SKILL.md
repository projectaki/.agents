---
name: factory-context
description: "Use only when the human explicitly starts the context lifecycle for a software change or investigation. Read the issue, codebase, and relevant local or authoritative online documentation; return the complete evidence needed to begin planning, or identify what is missing."
---

# Factory Context

Build the evidence base for planning. Do not plan or implement.

## Workflow

1. Read the request and complete issue, including linked artifacts. Extract the
   outcome, scope, acceptance criteria, constraints, and unresolved decisions.
2. Read applicable repository instructions, then trace the relevant code,
   tests, configuration, and history. Establish current behavior, architecture,
   dependencies, conventions, and likely change surface.
3. Read relevant repository documentation. Search authoritative online sources
   when external APIs, libraries, standards, or current behavior matter; record
   the source and applicable version or date.
4. Cross-check the evidence. Separate facts, inferences, and unknowns. Resolve
   discoverable gaps before asking the human.
5. Return a self-contained context packet with:
   - task, outcome, scope, acceptance criteria, and constraints
   - current behavior and relevant architecture
   - relevant files, symbols, tests, and documentation
   - repository conventions and external sources
   - assumptions, conflicts, unknowns, and only essential questions
   - verdict: `ready`, `needs-clarification`, or `blocked`

Return `ready` only when a planner can understand what must change, how the
current system works, which constraints apply, and which evidence supports
those conclusions without repeating discovery.

Stop after the context packet or the smallest set of blocking questions.
