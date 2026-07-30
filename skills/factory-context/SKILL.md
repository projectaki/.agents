---
name: factory-context
description: "Use only when the human explicitly starts the context lifecycle for a software change or investigation. Research the issue, codebase, and relevant local or authoritative online documentation; return planning evidence or identify what is missing."
---

# Factory Context

Build the evidence needed for planning. Do not plan or implement.

When orchestrated, the primary thread must delegate this skill to the routed
tier worker. That worker completes the workflow without spawning another
lifecycle actor.

## Workflow

1. Read the complete request and linked artifacts. Extract the outcome, scope,
   acceptance criteria, constraints, and open decisions.
2. Trace relevant code, tests, configuration, history, and repository
   documentation. Use authoritative online sources when current external APIs,
   libraries, standards, or behavior matter.
3. Separate confirmed facts, reasonable inferences, conflicts, and unknowns.
4. Resolve discoverable gaps, then return one self-contained context packet or
   the smallest set of blocking questions.

## Context packet

Include:

- requested change, outcome, scope, and acceptance criteria
- current behavior and relevant architecture
- relevant files, symbols, entry points, tests, reliable observable boundaries,
  side effects, consumers, and documentation
- project conventions, constraints, and authoritative sources
- facts, inferences, conflicts, assumptions, unknowns, and material questions

Include history only when it still defines behavior, compatibility, migration,
or an open decision. Omit superseded requirements, discarded approaches, and
correction history.

## Human report

When orchestrated, keep exhaustive evidence in the agent packet and write one
`report.md` without internal IDs or bookkeeping.

- Use plain language, short sentences, spacing, and descriptive headings.
- Start with **At a glance** and the readiness.
- Prefer **Ready for planning**, **Needs clarification**, or **Blocked**.
- Do not use JSON, YAML, key-value fields, raw command output, or internal agent
  terms.
- Use technical names only when they help verification, and explain why they
  matter.
- Use bullets for facts and numbered lists only for ordered steps or questions.
  Avoid dense tables.
- Label **Confirmed**, **Likely**, and **Still unknown** clearly.
- Omit empty sections.

Use these headings when relevant:

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

End **Readiness** with **Yes**, **Not yet**, or **Blocked**, followed by the
reason. Mark **Ready for planning** only when a planner can proceed without
repeating discovery.
