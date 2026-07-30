---
name: factory-handoff
description: Persist immutable lifecycle checkpoints, route reasoning, approval dispositions, and a readable lifecycle timeline while restoring deterministic current handoffs under ~/.agents-db. Use after every lifecycle result, before and after routing to another lifecycle, and whenever an orchestrator resumes, audits, observes, or reconciles task state across agent turns, context compaction, and restarts.
---

# Factory Handoff

Use this skill in one of three modes: **persist** a lifecycle result, **record**
a router evaluation or disposition, or **resume** an existing task.

## Resolve the deterministic path

Run the bundled resolver relative to this skill's directory:

```bash
<skill-directory>/scripts/resolve-handoff-path.sh <lifecycle>
<skill-directory>/scripts/resolve-handoff-path.sh --checkpoint <sequence> <lifecycle>
<skill-directory>/scripts/resolve-handoff-path.sh --route <sequence> <from> <to>
```

The commands return:

```text
$HOME/.agents-db/<project_slug>/<branch_slug>/<lifecycle_slug>
$HOME/.agents-db/<project_slug>/<branch_slug>/history/checkpoints/<sequence>-<lifecycle_slug>
$HOME/.agents-db/<project_slug>/<branch_slug>/history/routes/<sequence>-<from>--<to>
```

Use `--root` to return the branch task root, `--history` to return the history
root, and `--timeline` to return the human-readable lifecycle timeline. The
resolver:

- derives the project from the Git root basename, falling back to the workspace basename;
- derives the branch from Git, using `detached-<short_sha>` or `no-branch` when necessary;
- lowercases names, replaces `/` with `--`, and replaces unsafe characters with `-`;
- accepts only lifecycles defined by the orchestrator protocol.

Never invent another path or fall back to a temporary directory. If the path cannot be created or written, report the blocker and do not advance the lifecycle.

## Storage layout

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
        └── diagrams/
```

- `state.md` is the canonical task record and pointer to the latest handoff.
- `change-assurance-report.md` is the canonical final-diff accountability and
  behavioral-path evidence report. Create it during implementation and replace
  it with the current snapshot as the diff or evidence changes.
- `handoff.md` is the canonical lifecycle handoff. Replace it whenever that
  lifecycle completes again and describe only the latest checkpoint.
- `report.md` is the lifecycle's only human review document. Follow the
  orchestrator's `HUMAN_REPORTS.md` contract. Keep internal IDs, state,
  traceability matrices, and recovery metadata in agent-oriented files.
- `history/checkpoints/` is an append-only observation and audit record. It
  never changes canonical routing or resume behavior.
- `history/routes/` is an append-only record of router evaluations and their
  dispositions. A rejected proposal remains observable even though no
  lifecycle transition occurred.
- `history/timeline.md` is a derived audit view of the lifecycle run, not a
  lifecycle report.
  Replace it from immutable checkpoint and route records after each history
  event. It is noncanonical and can always be rebuilt.
- Each checkpoint directory contains `manifest.md` and a self-contained
  `snapshot/` tree. Copy the canonical handoff and every mutable branch-task
  file it references into `snapshot/`, preserving each path relative to the
  branch task root. This keeps historical relative links valid after canonical
  files change.
- `context.md` contains detailed context that would make `handoff.md` unnecessarily large. Create it only when useful.
- Store supporting files under `artifacts/`; use the fixed `images/` and `diagrams/` subdirectories for those media types.
- Reference every supporting file from `handoff.md` using paths relative to the lifecycle directory.

External references with their own durable identity, including Git commits and
permanent evidence URLs, remain references and do not need copying. Copy mutable
local references into the snapshot when they live elsewhere in the branch task
root. Import a mutable local file outside the branch task root into canonical
artifacts before snapshotting it. Do not retain credentials, secrets, or
unredacted sensitive data in either canonical or historical artifacts.

## Checkpoint identity and history

Use one monotonic `checkpoint_sequence` across the branch task. A lifecycle can
complete several times without changing the task revision, so never identify a
checkpoint by task revision alone.

Record only the current history counters and pointers in `state.md`:

```yaml
checkpoint_sequence: 3
latest_snapshot: history/checkpoints/000003-implementation/manifest.md
route_sequence: 2
latest_route_record: history/routes/000002-review--implementation/decision.md
```

For an existing task without these fields, treat the last sequence as `0` and
initialize an empty history. Never renumber or reuse a committed sequence. Do
not store the complete checkpoint or route history in `state.md`; canonical
state contains only what routing and recovery need now.

Write `manifest.md` with the checkpoint sequence, lifecycle, task revision,
assignment ID, invocation ID, attempt number, tier history, runtime-enforcement
status, escalation rationale when applicable, actor outcome, exit-gate result,
Git HEAD, dirty-worktree status, creation time, canonical handoff path, and an
inventory of copied files. Use SHA-256 for every copied-file checksum. Terminal
lifecycles without an actor use `invocation_id: null`. Use this manifest shape:

```yaml
checkpoint_sequence: 3
lifecycle: IMPLEMENTATION
task_revision: 1
invocation_id: implementation-r1-attempt-2
assignment_id: implementation-r1
attempt: 2
model_tier: standard
attempted_model_tiers: [fast, standard]
runtime: codex
worker_profile: standard-worker
resolved_model: gpt-5.6-terra
resolved_effort: medium
dispatch_mechanism: native_profile
runtime_enforcement: confirmed
escalation_rationale: Fast attempt omitted required acceptance-criteria evidence.
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

After a checkpoint is committed in `state.md`, its checkpoint directory is
immutable. Retain every checkpoint while the task is active. Archival and
retention after a terminal lifecycle are explicit policy decisions outside this
skill; do not silently prune history.

## Route decision history

After every router evaluation, allocate `route_sequence + 1` and write
`decision.md` before proposing or committing the route. Record:

- task revision, trigger event, current lifecycle, and source checkpoint;
- every permitted outgoing edge evaluated, its guard result, and supporting
  evidence;
- hard invariants and policy signals used, including risk, confidence, scope,
  assignment ID, attempt number, and any prior sequential escalation;
- selected lifecycle, edge, passed guard, and an evidence-backed rationale
  sufficient to audit the decision;
- invalidated artifacts and why they became stale;
- next actor role, initial abstract model tier, and resolved runtime details
  when known. A fresh assignment's initial tier is always `fast`;
- creation time and Git HEAD.

Use this decision shape:

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
escalation: null
next_actor:
  role: implementer
  model_tier: fast
created_at: <ISO-8601 UTC>
git_head: <commit-or-null>
```

Record decision factors and evidence, not private deliberation or hidden
chain-of-thought. For initial entry, use `from: initial` and
`source_checkpoint: null`.

Never replace `decision.md`. Under the temporary human approval gate, create
`disposition.md` after a rejection or after an approved lifecycle transition
has been committed to canonical state. Without that gate, write the committed
disposition after committing the lifecycle transition. Record the status,
decision time, authorization or rejection reason, approval reference when
applicable, and whether the lifecycle transition was committed. A pending
proposal has no `disposition.md`.

Use this disposition shape:

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

If new evidence causes reevaluation, allocate a new route sequence instead of
amending the earlier decision. This preserves reasoning that did not lead to a
transition and makes non-convergence observable.

## Lifecycle timeline

Regenerate `history/timeline.md` from checkpoint manifests, route decisions,
and route dispositions. Show:

- a run summary with lifecycle visit counts, edge counts, rework loops,
  rejected routes, escalations, and `AWAITING_INPUT` entries;
- each lifecycle visit and its checkpoint outcome;
- every proposed node-to-node route, including rejected proposals;
- the selected guard and concise rationale;
- task revision, assignment ID, invocation ID, attempt number, attempted model
  tiers, runtime enforcement, risk, confidence, and scope;
- invalidated artifacts, blockers, and approval disposition;
- relative links to the full immutable records.

Order entries chronologically and include checkpoint and route sequence IDs.
Use a compact event table with time, ID, event type, lifecycle or movement,
outcome or guard, rationale, and a relative record link. Put detailed evidence
only in the linked immutable record.
The timeline summarizes immutable records; it must not introduce facts absent
from them. A missing or stale timeline is an observability defect, not a reason
to route from history or override valid canonical state.

## Record a router evaluation

After the router selects an edge and before the route is proposed or committed:

1. Allocate `route_sequence + 1` and resolve the route directory.
2. Write and verify the complete immutable `decision.md`.
3. Update `route_sequence` and `latest_route_record` in `state.md` without
   changing the current lifecycle.
4. Regenerate and verify `history/timeline.md`.

After the route outcome is known:

1. For a rejection, write `disposition.md` with `status: rejected`.
2. For an approved or ungated route, first commit the new lifecycle in
   canonical state, then write `disposition.md` with `status: committed`.
3. Regenerate and verify the timeline.

If canonical state shows that a route committed but `disposition.md` is missing,
resume may write one recovered committed disposition using canonical evidence.
If the evidence is ambiguous, report the mismatch and do not infer an outcome.
Never rewrite a decision or disposition.

Every lifecycle requires:

```text
<lifecycle>/
├── handoff.md
├── report.md
├── context.md
└── artifacts/
    ├── images/
    └── diagrams/
```

`report.md` is the canonical human entry point and contains the information a
human needs to understand and approve that lifecycle result. The handoff links
to it first and does not duplicate it. Agent-only detail stays in `handoff.md`,
`context.md`, canonical packets, and supporting artifacts. For `ANALYSIS`,
`context.md` contains complete stable-ID traceability while `report.md` uses
plain names only.

Do not use timestamps or ad hoc handoff names in canonical paths.

Treat supplied packets, discussion, and earlier checkpoints as sources used to
derive the current checkpoint. Do not copy their commentary or narrate
superseded wording, corrected mistakes, discarded approaches, or prior versions.
Retain an earlier fact only when it remains an active decision, constraint,
risk, blocker, or required provenance. Git HEAD, task revision, validation
results, and artifact references are state data and should remain explicit.

The layout supports one active orchestrated task per project and branch. If `state.md` already exists, resume that task. Do not replace it with a different objective unless the human explicitly archives or clears the existing task state.

## Persist a lifecycle result

After an actor returns any lifecycle result and before the router selects the next lifecycle:

1. Resolve and create the lifecycle directory and required artifact directories.
2. Write and validate the lifecycle's single `report.md` using
   `HUMAN_REPORTS.md`. Run:

   ```bash
   python3 <skill-directory>/scripts/validate-human-report.py <lifecycle-directory>/report.md
   ```

   Fix every reported violation before checkpointing. This mechanical check is
   not a substitute for the required human readability edit.
3. Write the canonical `handoff.md` with:
   - a first link to the lifecycle's `report.md`;
   - task objective and acceptance criteria;
   - lifecycle, task revision, assignment ID, invocation ID, attempt number,
     current tier, attempted tiers, resolved runtime details, dispatch
     mechanism, runtime enforcement, actor outcome, and exit-gate result;
   - lifecycle output summary;
   - decisions, assumptions, and constraints;
   - canonical artifacts and evidence;
   - current change-assurance report when implementation has begun;
   - changed files and Git HEAD when applicable;
   - validation performed;
   - risks, blockers, and unresolved questions;
   - model-insufficiency signals and evidence, the next sequential tier when
     eligible, and inputs the lifecycle router needs when escalation is not
     eligible.
   Express each item as current state. Replace superseded values instead of
   appending a correction or change narrative.
4. Write optional detailed material to `context.md` and supporting files to
   `artifacts/`. For `ANALYSIS`, `context.md` must contain the complete internal
   traceability required by `ANALYSIS_REPORT.md`.
5. Allocate `checkpoint_sequence + 1`, resolve its deterministic checkpoint
   directory, and create the complete historical snapshot and `manifest.md`
   from the canonical files. Fail if that committed sequence already exists;
   never overwrite a historical checkpoint.
6. Verify the snapshot manifest, every copied file, every preserved relative
   reference, and every checksum.
7. Update root `state.md` with:
   - project and branch slugs;
   - task objective;
   - task revision;
   - status: `lifecycle_checkpointed` for a persisted actor result, `lifecycle_active` for `AWAITING_INPUT`, or `terminal` for `COMPLETED` and `CANCELLED`;
   - current and last-checkpointed lifecycle;
   - relative path to the latest handoff;
   - Git HEAD and dirty-worktree status;
   - pending transition, if any;
   - active assignment ID, active attempt, and attempted model tiers;
   - the committed checkpoint sequence;
   - relative path to the latest snapshot manifest;
   - update time.
8. Regenerate `history/timeline.md`.
9. Verify that `state.md`, canonical `handoff.md`, snapshot `manifest.md`,
   lifecycle timeline, and
   every canonical and historical referenced artifact are readable.
10. Return the branch task root, canonical handoff path, human report path, and
   snapshot manifest
   path.

Persist the canonical handoff, immutable snapshot, and state index as one
complete checkpoint. Do not mark the lifecycle checkpointed or append its
history pointer when validation fails.

When the orchestrator selects a replacement attempt, keep the canonical
lifecycle unchanged, update `state.md` to `lifecycle_active`, and persist the
next invocation with exactly the next tier. The completed checkpoint is the
immutable escalation decision evidence. Do not create a lifecycle route record
or self-edge for this invocation-control action.

`AWAITING_INPUT`, `COMPLETED`, and `CANCELLED` have no worker actor result. Persist their pause or terminal result immediately after committing entry into the lifecycle.

## Resume a task

1. Resolve the branch task root with `resolve-handoff-path.sh --root`.
2. Read `state.md`. If it does not exist, report that no resumable task exists at the deterministic path.
3. Read the latest `handoff.md` referenced by `state.md`.
4. Read all artifacts required for the next routing decision.
5. Compare persisted project, branch, Git HEAD, and dirty-worktree status with the current workspace.
6. Verify that `latest_snapshot` exists, its manifest agrees with the indexed
   sequence and lifecycle, and its checksums pass. For legacy state without
   history fields, report that history begins with the next checkpoint rather
   than treating the task as corrupt.
7. Treat unindexed checkpoint directories as incomplete writes. If the next
   sequence's manifest, checksums, actor result, and canonical handoff all match,
   finish the interrupted persist by indexing that snapshot in `state.md`.
   Otherwise report a blocker. Never route from, overwrite, or silently delete
   an unindexed checkpoint.
8. Return a resume packet containing the persisted lifecycle, revision, latest
   actor outcome, artifacts, latest snapshot, history mismatches, blockers, and
   pending transition.

Also verify the latest indexed route decision and disposition when present.
Treat an unindexed next-sequence route directory as an interrupted write. Index
it only when its immutable decision is valid, its source agrees with canonical
state, and no conflicting route exists; otherwise report a blocker. Never
overwrite or silently delete it.
When legacy `transition_history` exists, return a required migration: import
each entry into an immutable route record using only its available facts, mark
the record `provenance: legacy_state`, and remove the embedded history only
after validating every imported record. Regenerate a missing or stale timeline
from immutable records.

Historical snapshots are diagnostic evidence only. Do not choose a lifecycle,
reconstruct current state, or route from history. The primary orchestrator
consumes the resume packet and invokes the router from canonical state.
