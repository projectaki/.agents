# ANALYSIS Report Contract

The canonical human entry point for the `ANALYSIS` lifecycle is:

```text
<analysis-lifecycle-directory>/analysis-report.md
```

The report must be self-contained for understanding the change's system impact. Optimize for attention through ordering, grouping, tables, short bullets, and visual semantics—not by omitting information.

## Completeness invariants

- Include every known hotspot, affected or potentially affected surface, material risk, uncertainty, system boundary, and required verification mapping.
- Do not impose numerical limits on hotspots, nodes, surfaces, risks, maps, or checks.
- An overview may aggregate detail only when every aggregate expands into a detailed map or complete inventory entry in the same report.
- Essential understanding must not require opening another artifact.
- Supporting artifacts are allowed only for raw evidence too large to embed. Link each one from the relevant report entry.
- Every material claim includes an evidence reference.

## Stable IDs

Assign stable identifiers and reuse them throughout the report:

| Prefix | Meaning |
| --- | --- |
| `H#` | Hotspot requiring attention |
| `P#` | End-to-end behavioral path requiring change assurance |
| `S#` | Affected or potentially affected surface |
| `R#` | Material risk or regression concern |
| `U#` | Uncertainty or evidence gap |
| `V#` | Required verification check |

IDs remain stable when ANALYSIS is regenerated. Retire obsolete entries explicitly; do not silently renumber unrelated entries.

## Required reading order

### 1. Start here

Provide:

- one sentence describing the change;
- one sentence describing its system reach;
- one sentence describing the dominant failure concern;
- a compact classification table containing risk, scope, confidence, blast radius, and counts for hotspots, behavioral paths, surfaces, risks, uncertainties, and verification checks;
- a short reading guide pointing to the most important sections for this specific change.

This section is an orientation layer, not a substitute for the complete report.

### 2. Attention index

List every hotspot, ordered by severity and grouped by logical system area.

| ID | Severity | Area | What could go wrong | Why it matters | Related IDs |
| --- | --- | --- | --- | --- | --- |

Do not show only the highest-severity entries. If no hotspot exists, state why.

### 3. System impact

Begin with a system-level overview showing the complete flow between meaningful boundaries. Follow it with as many detailed maps as necessary to represent every affected path without crowding unrelated concerns into one diagram.

Every diagram must include:

- a one-sentence purpose and explicit instruction for what to notice;
- a legend before the diagram;
- direction of reading;
- stable `H#`, `P#`, and `S#` identifiers on relevant nodes;
- node change state;
- named relationships on edges;
- source references for inferred or uncertain paths.

Use these node states consistently:

| State | Meaning |
| --- | --- |
| `CHANGED` | Directly modified by the proposed work |
| `AFFECTED` | Not directly modified but behavior may change |
| `RETAINED` | Deliberately unchanged and relevant to understanding impact |
| `REMOVED` | Deleted or made unreachable by the proposed work |
| `UNCERTAIN` | Plausibly affected but not yet proven |

Color may reinforce a state but must never be its only indicator. Put the state in the node label. Use solid edges for evidenced relationships and dashed edges for uncertain or compatibility paths. Label every edge with its meaning, such as `calls`, `writes`, `reads`, `generates`, `publishes`, `invalidates`, or `authorizes`.

Do not add decorative nodes or unlabeled edges. A node appears only when it helps explain impact, a boundary, a hotspot, retained behavior, removal, or uncertainty.

### 4. Behavioral path inventory

Group the proposed change into meaningful end-to-end paths instead of treating
each file or edit as an independent behavior.

| ID | Trigger or caller | Path and affected surfaces | Highest reliable observable boundary | Expected behavior | Change category | Related risks | Planned proof |
| --- | --- | --- | --- | --- | --- | --- | --- |

Trace each path upward to the highest stable caller or user-visible boundary
whose assertions can reliably prove the changed behavior, and downward through
material side effects and consumers. Prefer one sufficient boundary check over
duplicative tests at every internal layer. Do not use a broad end-to-end test
when a smaller deterministic boundary proves the same claim.

Use these change categories:

- `non-behavioral`: documentation, formatting, generated output, or metadata
  with no runtime effect;
- `behavior-preserving`: mechanical refactor, rename, relocation, or deletion
  whose relevant behavior is intended to remain identical;
- `localized-behavior`: deterministic behavior contained within one component;
- `cross-boundary-behavior`: behavior crossing a service, process, persistence,
  permission, contract, or shared-consumer boundary;
- `experiential-behavior`: visual, interaction, animation, timing, or other
  behavior requiring human-observable proof when automation is insufficient.

Every affected `S#` must map to at least one `P#`, or be explicitly justified as
having no executable behavioral path.

### 5. Complete impact inventory

List every affected and potentially affected surface, grouped by subsystem and ordered by risk within each group.

| ID | State | Surface | Expected effect | Callers or consumers | Boundary | Related hotspots and risks | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |

Do not hide surfaces under catch-all entries such as “miscellaneous.” Aggregated entries must link to their complete expansion.

### 6. Risks and uncertainties

List every material risk and uncertainty separately.

| ID | Type | Severity | Trigger or unknown | Failure impact | Affected surfaces | Mitigation or evidence needed |
| --- | --- | --- | --- | --- | --- | --- |

Clearly distinguish evidence-backed risk from uncertainty. Include external consumers and unverifiable paths when they are relevant.

### 7. Verification coverage

Map every acceptance criterion, hotspot, surface, risk, and uncertainty that requires proof to one or more checks.

| ID | Proves | Check | Expected evidence | Required depth |
| --- | --- | --- | --- | --- |

The `Proves` column contains the relevant acceptance-criterion and `H#`, `P#`,
`S#`, `R#`, or `U#` references. Select the cheapest sufficient proof:
corroborated inspection for simple non-behavioral or behavior-preserving
changes, automated checks for deterministic behavior, and screenshot or video
only when automation cannot prove the relevant observable property. Any
intentionally unverified entry must state the rationale and residual risk.

### 8. Boundaries and decisions

Use compact tables or bullets for:

- intentionally unchanged behavior;
- removals;
- compatibility paths;
- assumptions;
- decisions already constrained by evidence;
- out-of-scope areas that are close enough to be mistaken as affected.

Reference the applicable stable IDs.

### 9. Planning implications

State only actionable downstream consequences:

- constraints the plan must preserve;
- system areas that need implementation steps;
- required reviewer perspectives;
- required verification depth;
- unresolved input that blocks planning.

### 10. Evidence index

List the repository files, symbols, tests, documentation, history, runtime observations, and supporting raw artifacts used by the analysis. Map evidence back to stable IDs where practical.

## Writing rules

- Prefer tables, short bullets, and captions over prose paragraphs.
- Put the conclusion before supporting detail.
- Order by severity first, then system flow or subsystem.
- State “none” rather than omitting a required section.
- Avoid repeating the same explanation; use stable-ID references.
- Keep labels concrete and domain-specific.
- Do not use “low attention span” as a reason to shorten the evidence set.
