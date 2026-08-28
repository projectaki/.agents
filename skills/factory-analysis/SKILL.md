---
name: factory-analysis
description: "Use only when the human explicitly starts analysis with an aligned task contract and current context. Determine system impact, behavioral paths, risks, and the smallest sufficient test and evidence scope without planning or editing files."
---

# Factory Analysis

Analyze the proposed change before planning. Remain read-only.

When orchestrated, the primary thread delegates analysis to the routed worker.
The worker must not spawn another lifecycle actor.

## Input

Require an aligned task contract, current context packet, and replication
baseline for a bug. Return the exact blocker when a required input is missing,
stale, or contradictory.

## Workflow

1. Trace each affected behavior from its highest relevant caller to the
   observable result, including data, permissions, side effects, integrations,
   and consumers.
2. Identify affected surfaces, boundaries, dependencies, unknowns, and direct
   or adjacent regression risks.
3. Group the change into stable behavioral paths and give material risks stable
   IDs for downstream traceability.
4. Inspect existing coverage. Map every path, acceptance criterion, and risk to
   the cheapest sufficient proof: inspection for simple non-behavioral work,
   otherwise focused automated tests, and visual evidence only when automation
   cannot prove the property.
5. State the implementation and verification implications without choosing an
   implementation approach.

Update the canonical proof-ledger data. Preserve each accepted claim and its
required proof. Add path and risk IDs. Close the inventory behind every
universal claim or block planning when it cannot be bounded.

When the orchestrator supplies Factory telemetry context, record material
investigations, unavailable evidence sources, failures, retries, and recovery
with the best-effort writer. Telemetry failure never changes analysis status.

## Output

Return:

- system impact, affected behavior, boundaries, dependencies, and consumers
- behavioral paths and observable outcomes
- ordered risks, failure modes, impact, and uncertainty
- existing coverage and required tests or evidence
- acceptance criteria and risks mapped to planned proof
- assumptions, exclusions, unknowns, blockers, and planning implications

Keep stable IDs and complete mappings in `context.md`. When orchestrated, also
write one plain-language `report.md` that explains impact, risks, required
proof, and readiness for planning. Follow the shared pattern in
`../factory-handoff/references/human-report-patterns.md` and use its Analysis
guidance.

Do not plan production changes, edit files, implement tests, or run checks.
