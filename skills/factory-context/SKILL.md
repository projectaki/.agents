---
name: factory-context
description: "Use only when the human explicitly starts context gathering with an aligned task contract. Research the codebase and relevant local or authoritative online documentation; return evidence for analysis or identify what is missing."
---

# Factory Context

Build the evidence needed for analysis. Do not analyze, plan, or implement.

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
`report.md` without internal IDs or bookkeeping. Follow the shared pattern in
`../factory-handoff/references/human-report-patterns.md` and use its Context
gathering guidance.

- Use plain language, short sentences, spacing, and descriptive headings.
- Prefer **Ready for analysis**, **Needs clarification**, or **Blocked**.
- Do not use JSON, YAML, raw command output, internal bookkeeping fields, or
  internal agent terms.
- Use technical names only when they help verification, and explain why they
  matter.
- Use bullets for facts and numbered lists only for ordered steps or questions.
- Label **Confirmed**, **Likely**, and **Still unknown** clearly.
- Omit empty sections.

After the shared headings, use these headings when relevant:

1. **What needs to change**
2. **What success looks like**
3. **What is and is not included**
4. **How it works today**
5. **Where the change is likely to happen**
6. **Important constraints**
7. **Evidence reviewed**
8. **What is still unclear**

Mark **Ready for analysis** only when an analyst can proceed without repeating
discovery.
