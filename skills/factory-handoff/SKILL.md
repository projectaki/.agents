---
name: factory-handoff
description: Persist immutable lifecycle checkpoint history and restore deterministic current handoffs under ~/.agents-db so an orchestrated implementation task can be observed or resumed across agent turns, context compaction, and restarts. Use after every lifecycle result, before routing to another lifecycle, and whenever an orchestrator resumes, audits, or reconciles persisted task state.
---

# Factory Handoff

Use this skill in one of two modes: **persist** a lifecycle result or **resume** an existing task.

## Resolve the deterministic path

Run the bundled resolver relative to this skill's directory:

```bash
<skill-directory>/scripts/resolve-handoff-path.sh <lifecycle>
<skill-directory>/scripts/resolve-handoff-path.sh --checkpoint <sequence> <lifecycle>
```

The commands return:

```text
$HOME/.agents-db/<project_slug>/<branch_slug>/<lifecycle_slug>
$HOME/.agents-db/<project_slug>/<branch_slug>/history/checkpoints/<sequence>-<lifecycle_slug>
```

Use `--root` to return the branch task root and `--history` to return the
checkpoint-history root. The resolver:

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
│   └── checkpoints/
│       └── 000001-<lifecycle_slug>/
│           ├── manifest.md
│           └── snapshot/
│               ├── change-assurance-report.md
│               └── <lifecycle_slug>/
│                   ├── handoff.md
│                   ├── context.md
│                   └── artifacts/
└── <lifecycle_slug>/
    ├── handoff.md
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
- `history/checkpoints/` is an append-only observation and audit record. It
  never changes canonical routing or resume behavior.
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

Record these fields in `state.md`:

```yaml
checkpoint_sequence: 3
latest_snapshot: history/checkpoints/000003-implementation/manifest.md
checkpoint_history:
  - sequence: 1
    lifecycle: IMPLEMENTATION
    task_revision: 1
    invocation_id: implementation-r1-attempt-1
    snapshot: history/checkpoints/000001-implementation/manifest.md
  - sequence: 2
    lifecycle: REVIEW
    task_revision: 1
    invocation_id: review-r1-attempt-1
    snapshot: history/checkpoints/000002-review/manifest.md
  - sequence: 3
    lifecycle: IMPLEMENTATION
    task_revision: 1
    invocation_id: implementation-r1-attempt-2
    snapshot: history/checkpoints/000003-implementation/manifest.md
```

For an existing task without these fields, treat the last sequence as `0` and
initialize an empty history. Keep one entry per committed checkpoint in sequence
order. Never renumber or reuse a committed sequence.

Write `manifest.md` with the checkpoint sequence, lifecycle, task revision,
invocation ID when applicable, actor outcome, exit-gate result, Git HEAD,
dirty-worktree status, creation time, canonical handoff path, and an inventory
of copied files. Use SHA-256 for every copied-file checksum. Terminal
lifecycles without an actor use `invocation_id: null`. Use this manifest shape:

```yaml
checkpoint_sequence: 3
lifecycle: IMPLEMENTATION
task_revision: 1
invocation_id: implementation-r1-attempt-2
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

The `ANALYSIS` lifecycle additionally requires:

```text
analysis/
├── handoff.md
├── analysis-report.md
└── artifacts/
    ├── images/
    └── diagrams/
```

`analysis-report.md` is the canonical human entry point and contains all essential impact understanding. The ANALYSIS handoff links to it first and does not duplicate its contents. ANALYSIS supporting artifacts contain only raw evidence too large to embed and are linked from the relevant report entries.

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
2. Write the canonical `handoff.md` with:
   - task objective and acceptance criteria;
   - lifecycle, task revision, actor outcome, and exit-gate result;
   - lifecycle output summary;
   - decisions, assumptions, and constraints;
   - canonical artifacts and evidence;
   - current change-assurance report when implementation has begun;
   - changed files and Git HEAD when applicable;
   - validation performed;
   - risks, blockers, and unresolved questions;
   - inputs the router needs for its next decision.
   Express each item as current state. Replace superseded values instead of
   appending a correction or change narrative.
3. Write optional detailed material to `context.md` and supporting files to `artifacts/`.
   For `ANALYSIS`, write and validate the required `analysis-report.md` before checkpointing.
4. Allocate `checkpoint_sequence + 1`, resolve its deterministic checkpoint
   directory, and create the complete historical snapshot and `manifest.md`
   from the canonical files. Fail if that committed sequence already exists;
   never overwrite a historical checkpoint.
5. Verify the snapshot manifest, every copied file, every preserved relative
   reference, and every checksum.
6. Update root `state.md` with:
   - project and branch slugs;
   - task objective;
   - task revision;
   - status: `lifecycle_checkpointed` for a persisted actor result, `lifecycle_active` for `AWAITING_INPUT`, or `terminal` for `COMPLETED` and `CANCELLED`;
   - current and last-checkpointed lifecycle;
   - relative path to the latest handoff;
   - Git HEAD and dirty-worktree status;
   - pending transition, if any;
   - the committed checkpoint sequence;
   - relative path to the latest snapshot manifest;
   - one compact append-only checkpoint-history entry;
   - update time.
7. Verify that `state.md`, canonical `handoff.md`, snapshot `manifest.md`, and
   every canonical and historical referenced artifact are readable.
8. Return the branch task root, canonical handoff path, and snapshot manifest
   path.

Persist the canonical handoff, immutable snapshot, and state index as one
complete checkpoint. Do not mark the lifecycle checkpointed or append its
history entry when validation fails.

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

Historical snapshots are diagnostic evidence only. Do not choose a lifecycle,
reconstruct current state, or route from history. The primary orchestrator
consumes the resume packet and invokes the router from canonical state.
