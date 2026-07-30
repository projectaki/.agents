# Analysis Human Report Contract

The canonical human entry point for the `ANALYSIS` lifecycle is:

```text
<analysis-lifecycle-directory>/report.md
```

Follow `HUMAN_REPORTS.md`. The report must let a human understand the proposed
change, its complete meaningful system impact, and the decisions needed before
planning.

## Completeness invariants

- Include every known hotspot, affected or potentially affected surface, material risk, uncertainty, system boundary, and required verification mapping.
- Do not impose numerical limits on hotspots, nodes, surfaces, risks, maps, or checks.
- Do not hide distinct affected endpoints, routes, jobs, consumers, commands, or
  state transitions behind aggregate counts.
- Essential understanding must not require opening another artifact.
- Supporting artifacts are allowed only for raw evidence too large to embed. Link each one from the relevant report entry.
- Every material claim includes an evidence reference.

## Internal traceability

Maintain stable hotspot, behavioral-path, surface, risk, uncertainty, and
verification IDs in the agent-oriented `context.md`. Keep the complete
many-to-many mappings there for planning, recovery, review, and verification.
Do not expose these IDs or ID-only mappings in `report.md`.

## Required reading order

### 1. Start here

Provide:

- one sentence describing the change;
- one sentence describing its system reach;
- one sentence describing the dominant failure concern;
- a direct readiness statement;
- the decisions or clarifications still needed.

This section is an orientation layer, not a substitute for the complete report.

### 2. What needs attention

List every hotspot in plain language, ordered by severity and grouped by
logical system area. For each one, state what could go wrong, why it matters,
and how the implementation or verification should address it.

Do not show only the highest-severity entries. If no hotspot exists, state why.

### 3. System impact

Begin with a system-level overview of the complete flow between meaningful
boundaries. Use prose, bullets, or a diagram according to whichever is easiest
to read. Follow it with detailed views only where they improve understanding.

For every diagram:

- use descriptive domain names with no internal IDs;
- show each meaningful endpoint, route, job, consumer, command, or transition
  as its own named node;
- split large diagrams by coherent flow or subsystem;
- label relationships with concrete verbs;
- state the purpose and what the reader should notice;
- omit the diagram when prose or a list is clearer.

When change state matters, use these plain labels:

| State | Meaning |
| --- | --- |
| Changed | Directly modified by the proposed work |
| Affected | Not directly modified but behavior may change |
| Retained | Deliberately unchanged and relevant to understanding impact |
| Removed | Deleted or made unreachable by the proposed work |
| Uncertain | Plausibly affected but not yet proven |

Color may reinforce a state but must never be its only indicator. Put the state in the node label. Use solid edges for evidenced relationships and dashed edges for uncertain or compatibility paths. Label every edge with its meaning, such as `calls`, `writes`, `reads`, `generates`, `publishes`, `invalidates`, or `authorizes`.

Do not add decorative nodes or unlabeled edges. A node appears only when it helps explain impact, a boundary, a hotspot, retained behavior, removal, or uncertainty.

### 4. Behavior that will change

Group the proposed change into meaningful end-to-end paths instead of treating
each file or edit as an independent behavior.

Use one short subsection per behavior. State:

- what starts it;
- the named components and surfaces it crosses;
- what the user or consuming system should observe;
- material side effects and consumers;
- the main regression concern;
- the planned proof.

Keep the formal change category and stable path mapping in `context.md`, not in
the human report. Trace every behavior to the highest reliable observable
boundary. Prefer one sufficient boundary check over duplicate checks at every
internal layer.

### 5. Complete affected-area inventory

List every affected and potentially affected surface, grouped by subsystem and ordered by risk within each group.

Prefer one compact block per subsystem. Name each surface separately and state
its change state, expected effect, callers or consumers, and supporting
evidence. Do not use catch-all entries such as "miscellaneous" or count-based
entries such as "4 endpoints."

### 6. Risks and uncertainties

List every material risk and uncertainty separately.

Use one short block per item with a descriptive heading. State whether the item
is a confirmed risk or an uncertainty, its severity, trigger or unknown,
failure impact, affected areas, and mitigation or evidence needed. Include
external consumers and paths that cannot yet be verified.

### 7. How success will be checked

Describe every required check using the behavior or risk name it proves. Select
the cheapest sufficient proof: corroborated inspection for simple
non-behavioral changes, automated checks for deterministic behavior, and
screenshot or video only when automation cannot prove the observable property.
State the rationale and residual risk for anything intentionally unverified.
Keep the exhaustive acceptance-to-risk-to-check matrix in `context.md`.

### 8. Boundaries and decisions

Use compact tables or bullets for:

- intentionally unchanged behavior;
- removals;
- compatibility paths;
- assumptions;
- decisions already constrained by evidence;
- out-of-scope areas that are close enough to be mistaken as affected.

### 9. Planning implications

State only actionable downstream consequences:

- constraints the plan must preserve;
- system areas that need implementation steps;
- required reviewer perspectives;
- required verification depth;
- unresolved input that blocks planning.

### 10. Evidence index

List only the repository files, symbols, tests, documentation, history, runtime
observations, and supporting raw artifacts that help the reviewer verify a
material claim. Keep the exhaustive evidence index and stable-ID mappings in
`context.md`.

## Writing rules

- Follow the table and diagram limits in `HUMAN_REPORTS.md`.
- Put the conclusion before supporting detail.
- Order by severity first, then system flow or subsystem.
- Omit empty sections unless their absence could be mistaken for incomplete
  analysis; in that case state that no items were found.
- Avoid repeating the same explanation, but repeat the plain name when needed;
  never substitute an opaque ID.
- Keep labels concrete and domain-specific.
