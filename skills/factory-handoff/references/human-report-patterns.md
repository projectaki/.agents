# Human lifecycle reports

Use this pattern for each lifecycle `report.md`. The report is for a human who
must understand the current result and decide what to do next. Keep complete
traceability, commands, and internal records in `handoff.md`, `context.md`, or
the assurance report.

Write every report in ASD-STE100 Simplified Technical English. Use short
sentences and the active voice. Define each term when first used. Do not use an
internal identifier without its plain-language meaning. Rewrite unclear or
noncompliant text before saving the report.

Write the report to the developer. The report is not published under the
developer's identity. State results directly. Do not impersonate the developer
or rewrite the report as if the developer wrote it.

## Contents

- [Common structure](#common-structure)
- [Rework](#rework)
- [Lifecycle patterns](#lifecycle-patterns)
- [Artifact rules](#artifact-rules)

## Common structure

Start each report with:

```markdown
# <Lifecycle>: <short outcome>

## At a glance

| | |
| --- | --- |
| Status | <ready, blocked, changes required, passed, or complete> |
| Scope | <one sentence> |
| Decision | <decision needed, or "None"> |

## <Lifecycle result>

<Use the smallest useful table, diagram, image, code example, or short list.>

## Remaining risk

<State the active risk or "None identified.">

## Next action

<Give one owner and action, or state that the task is complete.>
```

Use short sections and short sentences. Prefer no more than 350 words. Do not
exceed 500 words. Keep paragraphs below 100 words and lists below 9 items. Group
large result sets by the claim that they prove.

Use a two-column table for orientation and small comparisons. Use a Mermaid
diagram only when it makes a relationship or sequence easier to understand.
Use an image only when appearance is part of the result. Use a code example
only when a proposed or changed code shape is important to the human decision.

For a report longer than 250 words, include at least one table, diagram, image,
or code example. Do not add a visual that repeats the text.

## Rework

After review feedback or a human correction, add a small current-state table:

```markdown
## Feedback addressed

| Feedback | Current result |
| --- | --- |
| <plain-language feedback> | <resolved, open, or blocked result> |
```

Do not include a full revision history. Link the timeline when history is
needed.

## Lifecycle patterns

### Intake

Use a scope table and a short list of unanswered questions. Attach an existing
mockup or user example only when it is an input to the task.

### Context gathering

Show the current system boundary with a small Mermaid flow diagram when three
or more components interact. Useful artifacts are a current-state diagram and
redacted request, response, event, or data examples. Use **Ready for analysis**,
**Needs clarification**, or **Blocked** as the result. Mark the report ready only
when analysis can proceed without repeated discovery. Use these headings when
they contain useful information:

1. **What needs to change**
2. **What success looks like**
3. **What is and is not included**
4. **How it works today**
5. **Where the change is likely to happen**
6. **Important constraints**
7. **Evidence reviewed**
8. **What is still unclear**

### Replication

Show the shortest reproduction path, expected result, and observed result.
Useful artifacts are a minimal reproduction, a screenshot, a short video, or a
redacted log excerpt. Do not attach raw logs.

### Analysis

Show affected users, components, contracts, data, and operations. Use a flow or
state diagram when behavior crosses boundaries. Useful artifacts are an impact
map, a state transition diagram, and redacted contract examples. Explain the
impact, risks, required proof, and readiness for planning.

### Planning

Add a **Design preview** before the ordered steps when the change affects code
or system structure. Include:

- a small target-state Mermaid diagram
- one or two short, grounded code examples that show key files, types,
  function signatures, or composition
- labels that state that examples are proposed and can change during
  implementation

Keep each code example below 25 lines. Do not write a full implementation in
the plan. For a documentation or simple configuration change, state why a
diagram or code example does not help.

Useful plan artifacts are a larger target-state diagram, a redacted API or
event example, and a migration or rollout sequence. Put examples that are too
large for the report in `artifacts/examples/`.

### Implementation

Group changes by behavior or code area. Use a three-column table with area,
human effect, and result. Useful artifacts are before-and-after images,
generated contract diffs, schema examples, and code examples for a public API.

### Review

Lead with open findings. Give each finding a number, location, impact, and the
smallest safe correction. Use a small table when several findings affect
different areas. Attach an image or code example only when it makes a finding
clearer than a file and line reference.

### Video evidence

Embed or link the smallest set of images or videos that prove the visual
behavior. Give each artifact a claim and result. Do not use video when an
automated check proves the same property.

### Verification

Use a behavior-to-evidence table with result and remaining gap. Link visual
evidence beside the behavior that it proves. Keep exact commands and full test
output outside the report. Use the detailed
[verification report pattern](verification-report.md).

### Delivery

Show the pull request, conflict, approval, and CI dependency as a short flow
when delivery is blocked. Link durable remote records. Do not copy CI logs into
the report.

### Awaiting input

Use an options table with effect, risk, and the exact decision needed. Include
only choices that are supported by current evidence.

### Completed or cancelled

State the final result, delivered revision or reference, residual risk, and why
no next action remains.

## Artifact rules

Use artifacts only when they support a claim or decision in the report.

| Artifact | Use |
| --- | --- |
| `artifacts/images/` | Screenshots and still visual evidence |
| `artifacts/diagrams/` | Larger architecture, flow, state, or sequence diagrams |
| `artifacts/examples/` | Redacted code, payload, schema, event, or configuration examples |

Use text in the report for small diagrams and examples. Store a separate
artifact only when it is too large for quick reading or is reused. Link each
artifact from the claim that it supports. Never store secrets, tokens, personal
data, or unredacted production data.
