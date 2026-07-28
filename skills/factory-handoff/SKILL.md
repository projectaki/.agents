---
name: factory-handoff
description: Persist and restore deterministic lifecycle handoffs under ~/.agents-db so an orchestrated implementation task can resume across agent turns, context compaction, or restarts. Use after every lifecycle result, before routing to another lifecycle, and whenever an orchestrator resumes or reconciles persisted task state.
---

# Factory Handoff

Use this skill in one of two modes: **persist** a lifecycle result or **resume** an existing task.

## Resolve the deterministic path

Run the bundled resolver relative to this skill's directory:

```bash
<skill-directory>/scripts/resolve-handoff-path.sh <lifecycle>
```

The script returns:

```text
$HOME/.agents-db/<project_slug>/<branch_slug>/<lifecycle_slug>
```

Use `--root` instead of a lifecycle to return the branch task root. The resolver:

- derives the project from the Git root basename, falling back to the workspace basename;
- derives the branch from Git, using `detached-<short_sha>` or `no-branch` when necessary;
- lowercases names, replaces `/` with `--`, and replaces unsafe characters with `-`;
- accepts only lifecycles defined by the orchestrator protocol.

Never invent another path or fall back to a temporary directory. If the path cannot be created or written, report the blocker and do not advance the lifecycle.

## Storage layout

```text
~/.agents-db/<project_slug>/<branch_slug>/
├── state.md
└── <lifecycle_slug>/
    ├── handoff.md
    ├── context.md
    └── artifacts/
        ├── images/
        └── diagrams/
```

- `state.md` is the canonical task record and pointer to the latest handoff.
- `handoff.md` is the canonical lifecycle handoff. Replace it whenever that
  lifecycle completes again and describe only the latest checkpoint.
- `context.md` contains detailed context that would make `handoff.md` unnecessarily large. Create it only when useful.
- Store supporting files under `artifacts/`; use the fixed `images/` and `diagrams/` subdirectories for those media types.
- Reference every supporting file from `handoff.md` using paths relative to the lifecycle directory.

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
2. Write `handoff.md` with:
   - task objective and acceptance criteria;
   - lifecycle, task revision, actor outcome, and exit-gate result;
   - lifecycle output summary;
   - decisions, assumptions, and constraints;
   - canonical artifacts and evidence;
   - changed files and Git HEAD when applicable;
   - validation performed;
   - risks, blockers, and unresolved questions;
   - inputs the router needs for its next decision.
   Express each item as current state. Replace superseded values instead of
   appending a correction or change narrative.
3. Write optional detailed material to `context.md` and supporting files to `artifacts/`.
   For `ANALYSIS`, write and validate the required `analysis-report.md` before checkpointing.
4. Update root `state.md` with:
   - project and branch slugs;
   - task objective;
   - task revision;
   - status: `lifecycle_checkpointed` for a persisted actor result, `lifecycle_active` for `AWAITING_INPUT`, or `terminal` for `COMPLETED` and `CANCELLED`;
   - current and last-checkpointed lifecycle;
   - relative path to the latest handoff;
   - Git HEAD and dirty-worktree status;
   - pending transition, if any;
   - update time.
5. Verify that `state.md`, `handoff.md`, and every referenced artifact are readable.
6. Return the branch task root and handoff path.

Persist the handoff as one complete checkpoint. Do not mark the lifecycle checkpointed when validation fails.

`AWAITING_INPUT`, `COMPLETED`, and `CANCELLED` have no worker actor result. Persist their pause or terminal result immediately after committing entry into the lifecycle.

## Resume a task

1. Resolve the branch task root with `resolve-handoff-path.sh --root`.
2. Read `state.md`. If it does not exist, report that no resumable task exists at the deterministic path.
3. Read the latest `handoff.md` referenced by `state.md`.
4. Read all artifacts required for the next routing decision.
5. Compare persisted project, branch, Git HEAD, and dirty-worktree status with the current workspace.
6. Return a resume packet containing the persisted lifecycle, revision, latest actor outcome, artifacts, mismatches, blockers, and pending transition.

Do not choose the next lifecycle. The primary orchestrator consumes the resume packet and invokes the router.
