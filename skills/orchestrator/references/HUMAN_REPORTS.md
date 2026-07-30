# Human Lifecycle Report Contract

Every completed lifecycle writes exactly one human report:

```text
<lifecycle-directory>/report.md
```

The report exists for alignment and approval. Write it only for the person
deciding whether the work is understood, safe, and ready to continue.
`handoff.md`, `context.md`, state files, traceability maps, and evidence indexes
remain the agent-oriented record.

## Separation from agent records

- Derive the report from the complete lifecycle result, but do not copy the
  internal packet into it.
- Keep stable IDs, cross-reference matrices, fingerprints, routing fields,
  invocation metadata, and exhaustive evidence bookkeeping in agent records.
- Do not use internal IDs such as `P4`, `H3`, `R7`, `G2`, or `E5` in headings,
  prose, diagrams, or table cells. Replace each reference with the plain name
  of the behavior, risk, component, or check.
- Never make the reader look up an ID to understand a sentence.
- Include file paths, symbols, commit hashes, and external identifiers only
  when they help the reader verify or locate something.
- The human report may summarize agent records, but it must not omit a
  decision, uncertainty, risk, affected behavior, or scope boundary that could
  change human approval.

## Writing

- Start with the outcome, readiness, or decision needed.
- Use plain, direct language and the project's domain terms.
- Prefer short sections, bullets, and small repeated blocks.
- Avoid lifecycle jargon and abstract labels when an ordinary description is
  clearer.
- Do not use phrases such as "faithful port", "divergent decision point",
  "contract delta", "evidence plane", or similar invented shorthand. State the
  concrete behavior or difference.
- Remove process history, discarded approaches, raw command output, and agent
  commentary unless they affect the current decision.
- Explain any necessary technical term at first use.

## Tables

Use a table only when the reader needs to compare the same small set of fields
across several items.

- Prefer 2 or 3 columns. Do not exceed 4 columns.
- Do not place lists, paragraphs, multiple identifiers, or several evidence
  links in one cell.
- Replace a wide matrix with one subsection per behavior, risk, plan step, or
  decision.
- Replace sparse tables with bullets.
- If a table becomes hard to scan at normal Markdown width, restructure it.

## Diagrams

Create a diagram only when it makes an important relationship easier to
understand than a short list or compact prose. A report does not need a
diagram.

Before keeping a diagram, confirm that a reviewer can understand its purpose,
starting point, flow, and conclusion without consulting another section. Delete
or redraw it when that test fails.

- Use descriptive domain labels. Do not put internal IDs in nodes or edges.
- Do not combine distinct endpoints, routes, jobs, consumers, commands, or
  state transitions into a count-based node such as "4 endpoints".
- When those items matter to impact or behavior, show each one as its own named
  node. If the result is too large, split the view by coherent user flow or
  subsystem and provide a complete plain-language inventory.
- Never aggregate merely to make a diagram fit. Omit the diagram when a list is
  clearer.
- Label relationships with concrete verbs such as `calls`, `reads`, `writes`,
  `publishes`, or `redirects`.
- Show only information needed for the diagram's stated purpose.
- Use color only as a secondary cue. Put change state in ordinary words when
  the distinction matters.
- Give each diagram one sentence explaining what it shows and what the reader
  should notice.

## Required shape

Use the smallest set of sections that covers:

1. the outcome or proposed change;
2. what is included and intentionally unchanged;
3. affected users, behavior, systems, and data;
4. material risks and unknowns;
5. the work completed or planned in this lifecycle;
6. how success will be checked;
7. blockers, decisions, or approval needed;
8. a direct readiness statement.

Omit empty sections. Use descriptive headings rather than these numbers when a
domain-specific heading is clearer.

## Final edit

Read the report once as a reviewer who has not seen the agent packets.

- Replace every unexplained ID and cross-reference with its meaning.
- Replace jargon with a concrete statement.
- Break up every crowded table.
- Remove every diagram that takes more effort to decode than the text it
  replaces.
- Confirm that the report alone supports the requested human decision.
