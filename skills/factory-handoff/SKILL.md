---
name: factory-handoff
description: "Persist or resume compact Factory task state under ~/.agents-db. Keep one task contract, one assurance record, one current report, and one append-only history file with deterministic routing and integrity checks."
---

# Factory Handoff

Keep canonical Factory state small and current.

## Task root

Resolve the active project and branch task root:

```bash
<skill-directory>/scripts/resolve-task-root.sh
```

The helper derives project identity from the shared Git repository, so linked
worktree folder names do not create projects. Use `--discover` to list the
canonical path, matching legacy paths, and unverified paths whose repository
is unavailable. Inspect existing records before selecting a task root. Keep
using an existing task root when resuming it. Never merge or move records
implicitly. Save `repository_identity` from discovery for future lookup after a
worktree is removed.

Use this layout:

```text
<task-root>/
├── task.json
├── assurance.json
├── report.md
├── history.jsonl
├── artifacts/
└── telemetry/events.jsonl
```

Create `artifacts/` only when evidence needs a durable local file. Telemetry is
optional and noncanonical.

Read [the record contract](references/records.md) before creating or changing
canonical records.

## Persist

1. Replace `task.json`, `assurance.json`, and `report.md` with complete current
   representations. Omit `assurance.json` only before triage completes.
2. Keep the report concise. State the current result, remaining risk, decision,
   and next action. Do not copy machine mappings into it.
3. Append one checkpoint and route decision with the deterministic helper:

   ```bash
   python3 <skill-directory>/scripts/checkpoint.py \
     --task-root <task-root> \
     --lifecycle <lifecycle> \
     --outcome <outcome> \
     --reason '<plain evidence-backed reason>'
   ```

   The helper generates the timestamp, captures hashes and Git state, selects
   the guarded next lifecycle, and appends one locked JSON line. It rejects
   outcomes that do not belong to the selected lifecycle before writing history.
   Use a concrete result in `--reason`; do not submit placeholder text.
   When checking an uncertain submission, add `--preview` to validate records
   and inspect the proposed checkpoint and route without writing files. Preview
   does not reserve state; the actual submission validates current files again.
4. Validate the complete current records:

   ```bash
   python3 <skill-directory>/scripts/validate-records.py <task-root>
   ```

Checkpoint before a supervised return, while awaiting input, after the
implementation commit, before and after a remote write, and at completion or
cancellation. Do not create separate route files, snapshots, copied ledgers,
empty artifact directories, or generated timelines.

## Resume

1. Resolve the task root and validate the records.
2. Read the final valid history line as current lifecycle state.
3. Confirm its task revision, file hashes, Git head, branch, and dirty state.
4. Treat changed canonical files without a newer history entry as an
   interrupted write. Reconcile only when the intended change is unambiguous.
   Otherwise await human input.
5. Use the stored `next_lifecycle`. Never reconstruct current state from
   telemetry. A stale completion is not a current success.

## Authorized follow-up work

When later authorized work changes behavior or the reviewed revision, update
its contract and short current report. Increment `task_revision` for changed
behavior or scope. Keep authority already granted for the follow-up explicit.
Reset the assurance verdict to `unverified`. Replace affected evidence with
planned proof until it executes, or retain it with the verified reuse basis
specified in the record contract.

Append a checkpoint with `--lifecycle COMPLETED --outcome reopened` before
further work. The helper selects triage for a changed contract and
implementation for a revision correction. This is an event in existing stages,
not a new review or approval step. Earlier delivery entries remain history.
Classify a later finding by its cause; do not call a new requirement a missed
defect. Link related sessions and detailed artifacts instead of copying them.

If only legacy `state.md` exists, report that the task uses the removed Factory
schema. Do not guess or silently migrate it.

## Safety

Never persist secrets, credentials, customer data, private URLs, raw logs, or
private reasoning. Store concise decisions and evidence references. Git commits
preserve product revisions. `history.jsonl` preserves routing and checkpoint
history.
