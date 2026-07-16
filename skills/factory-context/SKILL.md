---
name: factory-context
description: "Use only when the human explicitly starts the context lifecycle for a software change or investigation. Read the issue, codebase, and relevant local or authoritative online documentation; return the complete evidence needed to begin planning, or identify what is missing."
---

# Factory Context

Build the evidence base for planning. Do not plan or implement.

## Workflow

1. Read the request and complete issue, including linked artifacts. Extract the
   outcome, scope, acceptance criteria, constraints, and unresolved decisions.
2. Spawn exactly one `context-researcher` subagent to perform repository and
   documentation discovery. Give it the complete request, supplied artifacts,
   repository or worktree, applicable instructions, and the evidence needed for
   this packet.
3. Ask the subagent to trace the relevant code, tests, configuration, history,
   and repository documentation. It may search authoritative online sources
   when external APIs, libraries, standards, or current behavior matter.
4. Wait for the subagent, then cross-check its findings against the request.
   Separate confirmed facts, reasonable inferences, and unknowns. Use a focused
   follow-up with the same subagent for a material omission when supported.
5. Resolve discoverable gaps before asking the human, then return one
   self-contained context packet.

Keep repository exploration, command output, and working notes inside the
subagent. The main session should read only enough repository state to prepare
the delegation, reconcile conflicting evidence, or fill a specific gap. Do not
repeat the subagent's full discovery in the main session.

If repository policy or the runtime prevents subagent use, perform the research
in the main session and state that limitation in the final packet.

## Evidence to include

- the requested change, desired outcome, scope, and acceptance criteria
- current behavior and the relevant architecture
- relevant files, code areas, tests, documentation, and history
- project conventions, constraints, and authoritative external sources
- confirmed facts, reasonable inferences, conflicts, assumptions, and unknowns
- only the questions whose answers materially change the work

## Human-readable output (current)

This is the current presentation contract. Keep it separate from the research
workflow so it can be replaced later without changing how evidence is gathered.

Write for a human reviewer:

- Use plain language, short sentences, generous spacing, and descriptive
  headings.
- Start with a brief **At a glance** summary of the change and its readiness.
- Prefer ordinary names such as **Ready for planning**, **Needs clarification**,
  and **Blocked** over machine-style values or internal lifecycle identifiers.
- Do not return JSON, YAML, key-value fields, raw command output, or internal
  agent terminology.
- Avoid unexplained jargon and abbreviations. Include file paths, code symbols,
  versions, and identifiers only when they help the reviewer verify or locate
  evidence, and explain why each one matters.
- Use bullets for scan-friendly facts and numbered lists only for ordered steps
  or questions. Do not compress unrelated facts into dense tables.
- Clearly distinguish **Confirmed**, **Likely**, and **Still unknown**. Never
  present an inference as a fact.
- Omit empty sections.

Use these headings when they apply:

1. **At a glance**
2. **What needs to change**
3. **What success looks like**
4. **What is and is not included**
5. **How it works today**
6. **Where the change is likely to happen**
7. **Important constraints**
8. **Evidence reviewed**
9. **What is still unclear**
10. **Readiness**

End **Readiness** with a direct sentence beginning with **Yes**, **Not yet**, or
**Blocked**, followed by the reason in plain language.

Mark the task **Ready for planning** only when a planner can understand what
must change, how the current system works, which constraints apply, and which
evidence supports those conclusions without repeating discovery.

Stop after the context packet or the smallest set of blocking questions.
