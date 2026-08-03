---
name: factory-handoff
description: Persist immutable lifecycle checkpoints, route decisions and dispositions, and a readable timeline; restore deterministic current handoffs under ~/.agents-db. Use after each lifecycle result, around routing, and when resuming, auditing, or reconciling Factory state.
---

# Factory Handoff

Use 1 mode: persist a lifecycle result, record a route, or resume a task.

## Paths

Run the bundled resolver:

```bash
<skill-directory>/scripts/resolve-handoff-path.sh <lifecycle>
<skill-directory>/scripts/resolve-handoff-path.sh --checkpoint <sequence> <lifecycle>
<skill-directory>/scripts/resolve-handoff-path.sh --route <sequence> <from> <to>
```

It returns:

```text
$HOME/.agents-db/<project_slug>/<branch_slug>/<lifecycle_slug>
$HOME/.agents-db/<project_slug>/<branch_slug>/history/checkpoints/<sequence>-<lifecycle_slug>
$HOME/.agents-db/<project_slug>/<branch_slug>/history/routes/<sequence>-<from>--<to>
```

Use `--root`, `--history`, or `--timeline` for those paths. The resolver:

- uses the Git root basename, else workspace basename, for the project
- uses the Git branch, `detached-<short_sha>`, or `no-branch`
- lowercases names, changes `/` to `--`, and unsafe characters to `-`
- accepts only `factory-orchestrator` lifecycles

Never invent or use a temporary fallback path. If the resolved path is not
writable, report the blocker and do not advance.

## Layout

```text
~/.agents-db/<project_slug>/<branch_slug>/
├── state.md
├── change-assurance-report.md
├── history/
│   ├── timeline.md
│   ├── checkpoints/
│   │   └── 000001-<lifecycle_slug>/
│   │       ├── manifest.md
│   │       └── snapshot/
│   │           ├── change-assurance-report.md
│   │           └── <lifecycle_slug>/
│   │               ├── handoff.md
│   │               ├── report.md
│   │               ├── context.md
│   │               └── artifacts/
│   └── routes/
│       └── 000001-<from_lifecycle>--<to_lifecycle>/
│           ├── decision.md
│           └── disposition.md
└── <lifecycle_slug>/
    ├── handoff.md
    ├── report.md
    ├── context.md
    └── artifacts/
        ├── images/
        ├── diagrams/
        └── examples/
```

- `state.md`: canonical task state and latest-handoff pointer.
- `change-assurance-report.md`: replaceable current diff/path/evidence record,
  created during implementation.
- `handoff.md`: replaceable latest result for 1 lifecycle.
- `report.md`: that lifecycle's only human document; no internal bookkeeping.
- `context.md`: optional detail that would bloat `handoff.md`.
- `artifacts/`: supporting files; put media in `images/` or `diagrams/`, and
  redacted code, payload, schema, event, or configuration samples in
  `examples/`.
- `history/checkpoints/`: append-only observations; never route from them.
- `history/routes/`: append-only decisions and dispositions, including rejected
  proposals.
- `history/timeline.md`: rebuildable, noncanonical view of immutable history.

Link artifacts from `handoff.md` with lifecycle-relative paths. A checkpoint
snapshot must copy the canonical handoff and every mutable branch-task file it
references, preserving branch-root-relative paths. Keep durable Git and
permanent URL references external. Import mutable files outside the task root
into canonical artifacts first. Never persist secrets or unredacted sensitive
data.

Use canonical names only; no timestamps or ad hoc handoff names. One active task
is allowed per project and branch. Resume an existing `state.md`; replace its
objective only after explicit archive or clear.

## Checkpoints

Use 1 monotonically increasing `checkpoint_sequence` per branch task. Repeated
lifecycle runs still get new sequences. Store only current counters and pointers
in `state.md`:

```yaml
checkpoint_sequence: 3
latest_snapshot: history/checkpoints/000003-implementation/manifest.md
route_sequence: 2
latest_route_record: history/routes/000002-review--implementation/decision.md
```

For legacy state without these fields, start at `0`. Never reuse, renumber,
overwrite, or prune committed sequences. Retention after a terminal lifecycle
requires separate explicit policy.

Write `manifest.md` in this shape:

```yaml
checkpoint_sequence: 3
lifecycle: IMPLEMENTATION
task_revision: 1
invocation_id: implementation-r1-attempt-2
assignment_id: implementation-r1
attempt: 2
model_tier: standard
attempted_model_tiers: [fast, standard]
runtime: <runtime>
worker_profile: standard-worker
resolved_model: <model>
resolved_effort: medium
dispatch_mechanism: native_profile
runtime_enforcement: confirmed
escalation_rationale: Fast attempt omitted required acceptance-criteria evidence.
selection_rationale: Medium reasoning difficulty requires evidence reconciliation.
worker_assessment:
  impact: low
  uncertainty: low
  reasoning_difficulty: medium
  proof_difficulty: low
  input_gaps: low
actor_outcome: succeeded
exit_gate: passed
git_head: <commit-or-null>
worktree_dirty: true
created_at: <ISO-8601 UTC>
canonical_handoff: implementation/handoff.md
files:
  - path: implementation/handoff.md
    sha256: <digest>
external_references: []
```

Include sequence, lifecycle, revision, assignment and invocation IDs, attempt,
tier history, runtime enforcement, applicable escalation rationale, actor
outcome, exit gate, Git state, UTC creation time, canonical handoff, all copied
files with SHA-256, and external references. Use `invocation_id: null` for
terminal lifecycles without actors. A checkpoint becomes immutable when indexed
in `state.md`.

## Route records

After every route evaluation, allocate `route_sequence + 1` and write
`decision.md` before proposing or committing the route. Include:

- revision, trigger, current lifecycle, and source checkpoint
- every permitted edge, guard result, and evidence
- invariants and signals: risk, confidence, scope, assignment, attempt, and
  earlier sequential escalation
- selected lifecycle, edge, passed guard, and auditable rationale
- stale artifacts and reasons
- next role, orchestrator-selected abstract tier, worker assessment, and runtime
  details when known
- UTC creation time and Git HEAD

Use this shape:

```yaml
route_sequence: 2
task_revision: 1
trigger: actor_result
from: REVIEW
source_checkpoint: history/checkpoints/000002-review/manifest.md
evaluated_edges:
  - to: VERIFICATION
    guard: implementation approved
    result: failed
    evidence: [finding-F1]
  - to: IMPLEMENTATION
    guard: implementation defect
    result: passed
    evidence: [finding-F1]
selected:
  to: IMPLEMENTATION
  edge: implementation defect
  rationale: Review found a blocking correctness defect in the persisted revision.
invalidated_artifacts: []
routing_signals:
  risk: medium
  confidence: high
  scope: local
worker_assessment:
  impact: medium
  uncertainty: low
  reasoning_difficulty: low
  proof_difficulty: medium
  input_gaps: low
  selected_tier: fast
  rationale: The approved plan resolves design decisions and bounds the change.
  escalation_triggers: [unexpected public contract, plan-invalidating dependency]
escalation: null
next_actor:
  role: implementer
  model_tier: fast
created_at: <ISO-8601 UTC>
git_head: <commit-or-null>
```

Use `from: initial` and `source_checkpoint: null` for initial entry. Record
evidence, not private reasoning. Never replace a decision.

A pending proposal has no `disposition.md`. With a temporary human gate, write
it after rejection or after an approved transition commits. Without a gate,
write it after the transition commits:

```yaml
route_sequence: 2
status: committed
decided_at: <ISO-8601 UTC>
authorization: human_approval
approval_reference: <reference-or-null>
rejection_reason: null
transition_committed: true
committed_lifecycle: IMPLEMENTATION
```

Never replace a disposition. New evidence requires a new route sequence.

## Timeline

Rebuild `history/timeline.md` after every history event from manifests,
decisions, and dispositions. Include:

- visit and edge counts, rework loops, rejected routes, escalations, and
  `AWAITING_INPUT` entries
- each checkpoint outcome and proposed route, including rejected routes
- selected guard, concise rationale, revision, assignment, invocation, attempt,
  attempted tiers, runtime enforcement, risk, confidence, and scope
- stale artifacts, blockers, approval disposition, and relative record links

Order by time and include sequence IDs. Use a compact table with time, ID, event,
lifecycle or movement, outcome or guard, rationale, and record link. Keep detail
in immutable records. The timeline may not add facts. Missing or stale timeline
is an observability defect, not routing authority.

## Record a route

Before proposing or committing:

1. Allocate the next route sequence and resolve its directory.
2. Write and verify immutable `decision.md`.
3. Update `route_sequence` and `latest_route_record` in `state.md` without
   changing lifecycle.
4. Rebuild and verify the timeline.

After the outcome:

1. For rejection, write `status: rejected`.
2. For approved or ungated routing, commit canonical lifecycle first, then write
   `status: committed`.
3. Rebuild and verify the timeline.

On resume, recover a missing committed disposition only from unambiguous
canonical evidence. Otherwise report a mismatch. Never rewrite route records.

## Persist a lifecycle result

Each lifecycle directory requires `handoff.md`, `report.md`, `context.md`, and
`artifacts/images/`, `artifacts/diagrams/`, and `artifacts/examples/`.
`report.md` is the human entry point. Write it with
[the shared human report pattern](references/human-report-patterns.md).
`handoff.md` links it first without duplicating it. Agent detail stays in
`handoff.md`, `context.md`, canonical packets, and artifacts. For `ANALYSIS`,
keep stable-ID traceability in `context.md`, not `report.md`.

Derive current state from inputs. Omit superseded wording, mistakes, discarded
approaches, and version narrative. Keep active decisions, constraints, risks,
blockers, provenance, Git state, revision, validation, and artifact references.

After any actor result and before routing:

1. Resolve and create the lifecycle and artifact directories.
2. Write the lifecycle's single `report.md`, then run:

   ```bash
   python3 <skill-directory>/scripts/validate-human-report.py <lifecycle-directory>/report.md
   ```

   Fix every issue and also edit for readability.
3. Write canonical `handoff.md` with:
   - first link to `report.md`
   - objective and acceptance criteria
   - lifecycle, revision, assignment, invocation, attempt, current and attempted
     tiers, worker assessment, selection rationale, runtime details, dispatch,
     enforcement, outcome, and exit gate
   - output summary, decisions, assumptions, constraints, artifacts, evidence,
     assurance report once implementation begins, changed files, Git HEAD,
     validation, risks, blockers, and open questions
   - worker evidence, orchestrator exit-gate assessment, failure classification,
     model-insufficiency evidence, next eligible tier, or routing inputs when
     escalation is ineligible
4. Put optional detail in `context.md` and supporting files in `artifacts/`.
5. Allocate the next checkpoint, create its snapshot and manifest, and fail if
   the directory exists.
6. Verify the manifest, copied files, relative links, and checksums.
7. Update `state.md` with project and branch slugs, objective, revision, status,
   current and last-checkpointed lifecycle, latest handoff, Git state, pending
   transition, active assignment and attempt, attempted tiers, checkpoint
   sequence, snapshot manifest, and update time. Use:
   - `lifecycle_checkpointed` for an actor result
   - `lifecycle_active` for `AWAITING_INPUT`
   - `terminal` for `COMPLETED` or `CANCELLED`
8. Rebuild the timeline.
9. Verify state, canonical handoff, manifest, timeline, and every referenced
   canonical and historical artifact are readable.
10. Return the task root, canonical handoff, human report, and snapshot manifest.

Treat the handoff, snapshot, and state index as 1 atomic checkpoint. Do not index
or mark checkpointed if validation fails.

For a replacement attempt, keep the lifecycle unchanged, set state to
`lifecycle_active`, and persist the orchestrator's new assessment. A
reasoning-quality escalation selects exactly the next tier. The prior checkpoint
is escalation evidence. Do not create a route or self-edge.

`AWAITING_INPUT`, `COMPLETED`, and `CANCELLED` have no worker result. Persist
them immediately after lifecycle entry.

## Resume

1. Resolve the task root with `--root`.
2. Read `state.md`; if absent, report no resumable task at that path.
3. Read its latest `handoff.md` and routing inputs.
4. Compare persisted project, branch, Git HEAD, and dirty state with the
   workspace.
5. Verify the indexed snapshot exists and its sequence, lifecycle, and checksums
   match. For legacy state, start history at the next checkpoint.
6. Treat unindexed checkpoint directories as interrupted writes. Index the next
   one only when its manifest, checksums, actor result, and canonical handoff
   match; otherwise block. Never route from, overwrite, or delete it.
7. Verify the latest indexed route and disposition. Index an unindexed next
   route only when its decision is valid, its source matches canonical state,
   and no conflict exists; otherwise block. Never overwrite or delete it.
8. Return lifecycle, revision, latest outcome, artifacts, snapshot, history
   mismatches, blockers, and pending transition.

If legacy `transition_history` exists, require migration. Import each entry into
an immutable route record using only available facts, mark
`provenance: legacy_state`, validate all imports, then remove embedded history.
Rebuild a missing or stale timeline.

Historical snapshots are diagnostic only. Never choose a lifecycle, rebuild
current state, or route from history. The primary orchestrator routes from the
canonical resume packet.
