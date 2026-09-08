---
name: factory-handoff
description: "Persist or resume compact Factory state under ~/.agents-db. Validate action prerequisites and publish current documents with recoverable, repeatable checkpoints."
---

# Factory Handoff

Keep one current contract, assurance record, report, and append-only history.
Read [the record contract](references/records.md) when creating or updating them.

## Locate and restore

Run `<skill-directory>/scripts/resolve-task-root.sh --discover`. The helper uses
shared Git identity and the exact branch name to avoid collisions. Save its
`repository_identity` and `branch` in the contract. Linked worktrees share
repository identity. Inspect discovered legacy locations before creating a new
task. Continue an existing task in its existing location. Never move, merge, or
rewrite old records implicitly.

Validate existing state with:

```bash
python3 <skill-directory>/scripts/validate-records.py <task-root>
```

Read the latest history result, current contract, and relevant evidence. A
stored next stage is a recommendation supported by that result. Select another
stage when new evidence justifies it, subject to action prerequisites. Never
reconstruct authority, scope, or completion from telemetry.

Old records remain readable where their schema permits. Missing current proof,
repository assessment, or reviewer identity must be supplied before dependent
work. Do not invent historical execution or approval. If only removed legacy
`state.md` exists, explain the incompatible format before resuming product work.

## Start an assignment

For the first intake, create the initial `task.json`, start an intake assignment
in the orchestrator, and establish the accepted contract before its checkpoint.
Later assignments use checkpointed state. Record a real worker identity before
it begins implementation or review:

```bash
python3 <skill-directory>/scripts/start-assignment.py \
  --task-root <task-root> --lifecycle <selected-stage> \
  --worker-id <worker-identity> --reason '<why this work is needed>'
```

The helper validates prerequisites and records assignment and run starts. Carry
its assignment and run identities into the result. Pass the same `--run-id`
while continuing automatically. Use a new run after returning to the user.
Apply its `timeout_seconds`, when present, through native worker control.
The helper does not launch or terminate native workers.

Only one assignment may be active per task. Resume an active worker instead of
starting another. Use `--interrupt` only after the earlier worker has stopped;
it closes the observed interruption and starts a replacement with a new run.
Do not treat an unobserved interruption gap as active work.

## Publish a result

Prepare complete `task.json`, `assurance.json`, and `report.md` in a temporary
input directory. Omit assurance only while investigation is still needed.
Keep the report to the result, remaining risk, decisions, and next action.
Replace outdated statements. Preserve detailed proof through references.

```bash
python3 <skill-directory>/scripts/checkpoint.py \
  --task-root <task-root> --input-dir <prepared-directory> \
  --expected-sequence <last-sequence-or-zero> --result-id <stable-result-identity> \
  --lifecycle <stage> --outcome <outcome> --progress yes \
  --reason '<observed result and remaining need>'
```

Use `--progress no` when no material requirement, uncertainty, defect, or proof
gap was resolved. Automatic execution requires this fact and measured duration.
The active assignment supplies identity and duration. Close it before human
waiting. Unknown historical time must remain unknown.

Supply `--next-lifecycle` and `--route-reason` to propose a different useful
stage. The helper validates its prerequisites. A proposal cannot bypass a stop,
required plan approval, independent review, or exact-revision proof. Use
`needs-triage` from implementation or review when a code assumption needs
investigation. A correctable code defect can return directly to implementation.

Use `--preview` for a read-only validation of a prepared result. Preview does not
reserve state. Reuse the same result identity when retrying a submission. The
helper returns the earlier result without appending a duplicate. A stale
expected sequence prevents overwriting another session's work.

The helper locks before reading state. A small pending update lets a later
submission finish interrupted document publication without guessing. It also
preserves the accepted contract once per task revision. Do not edit history,
contract snapshots, or pending updates. Direct current-file updates remain
readable for compatibility; use prepared input for recoverable publication.

Checkpoint before supervised returns and human waits, after implementation and
review, and around remote writes. Validate the published state. Basic events
are recorded automatically by the helpers. Telemetry is not task authority;
recording failure does not block product work. Report missing recording once.

## Authorized follow-up

For changed accepted behavior, scope, authority, or deliverable, increment the
task revision and preserve the authorized contract. Reset affected assurance to
`unverified`. Retain evidence only with a verified reuse basis. Submit
`COMPLETED` with outcome `reopened` before further work on a completed task.
Existing authorization remains applicable to the scope it covers. Do not ask
again merely because the task resumes.

Keep `artifacts/` for useful proof, `contracts/` for accepted revision contracts,
and `telemetry/` for runtime observations. `assignment.json` stores active
execution facts; `.checkpoint.lock` and `pending-checkpoint.json` protect
publication. Do not create full snapshots for every stage or copy transcripts.
Never persist secrets, customer data, private URLs, raw logs, or private reasoning.
