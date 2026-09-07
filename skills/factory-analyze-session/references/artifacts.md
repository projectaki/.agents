# Factory session artifacts

## Storage and boundaries

The current resolver selects `~/.agents-db/<project>/<branch-slug>/` from the
shared Git repository and branch. This is a task root, not a unique chat or run
archive. Linked worktrees share project identity. Discovery can also return
older paths and paths whose recorded repository is unavailable. Preserve their
separate identities unless explicit evidence connects them.

## Current artifacts

| Artifact | Stored information | Analytical use and limits |
| --- | --- | --- |
| `task.json` | Current objective, acceptance criteria, included and excluded scope, authority, deliverable, continuation mode, task revision, repository, base reference, optional repository identity and related sessions. | Establish the accepted result and authorized actions. It replaces previous versions; it does not preserve all earlier contracts. |
| `assurance.json` | Current risk assessment, worker-selection signals, required behaviors, risks, evidence, exceptions, blockers, reviewed Git revisions and branch, verdict, and routing flags. | Check proof coverage, review decisions, evidence reuse, and unresolved risk. It may be absent before triage. It is a current snapshot, not every review result. |
| `report.md` | Current human-readable result, remaining risk, decision, and next action. | Explain the final state. It is replaced at checkpoints and is not a transcript or full timeline. |
| `history.jsonl` | One JSON object per checkpoint: sequence, timestamp, stage, outcome, reason, next stage, stop and resume decisions, task revision, mode, Git state, and hashes of the current files. Optional worker identity, tier, attempt, active seconds, findings, and decisions. Completion includes a compact delivery summary and evidence references. | Reconstruct recorded transitions, corrections, pauses, and completions. Check file integrity against the latest checkpoint. Hashes detect changes but cannot restore old file contents. Optional fields can be null or absent. |
| `artifacts/` | Sanitized durable evidence files created when needed and referenced by records. | Inspect detailed proof behind a result. Neither this directory nor a full test-output archive is mandatory. A command reference alone is not captured command output. |
| `telemetry/events.jsonl` | Optional append-only runtime observations with occurrence and recording times. Supported events cover runs, actors, operations, failures, retries, recovery, waits, human decisions, external actions, workspace changes, artifact changes, and corrections. Correlation, duration, revision, and evidence fields are optional. | Explain retries, interruptions, waiting, operation durations, and observation defects. It never determines canonical task state or completion. Instrumentation support does not mean every session emitted the events. |
| `telemetry/summary.md` | Derived report written only when the telemetry summary helper is run. | A convenience summary, not an independent source. Check it against events; it can be absent or stale. |
| Referenced Git commits and external records | Product revisions and linked review, delivery, or test evidence. They live outside the task directory. | Verify the subject of a finding when available through authorized read access. An inaccessible link leaves an evidence gap. Do not fetch, checkout, or mutate the repository for this retrospective. |

Consult the sibling `factory-handoff/references/records.md` and its helper code
for the current field contract. Consult `factory-telemetry/scripts/record-event.py`
and `telemetry_schema.py` for supported event fields. Older records may use a
previous contract; do not describe a newly required field as an old execution
failure without historical support.

## Runtime analysis

The sibling `factory-telemetry/scripts/summarize-events.py` provides
`load_events`, `analyze`, and `render_summary`. Its command-line entrypoint
writes `telemetry/summary.md`, even with `--strict`. Do not run that entrypoint
against the source directory during a read-only analysis. Import the helper
with bytecode disabled and render its result in memory, or run it against a
temporary copy of the telemetry file outside the session directory. If the
helper fails, report the limitation and inspect valid events directly.

Verify the raw events before relying on summary metrics:

- The helper's completed-run active time is the sum of start-to-finish run
  durations. It does not subtract waits inside a run or merge overlapping runs.
  Describe it as recorded run duration unless active work is independently
  established. Checkpoint `active_seconds` means reported active work, but is
  optional. Do not add these two measurements together.
- Categorized operation time sums matched spans, including wait and recovery
  spans. Parallel or nested spans can overlap. It is not wall-clock duration or
  necessarily productive effort.
- Gaps between runs are unobserved time. They do not establish human waiting or
  active work. Use matched wait events to support attributed waiting.
- Incomplete runs and unmatched spans make totals partial. Surface malformed
  lines, duplicate events, invalid retry links, and unmatched starts or ends.
  Preserve file order for citations and use occurrence times for runtime order.
- Inspect correction events and their `corrects_event_id` links explicitly.
  The current summary helper does not apply corrections to earlier events.
  Separate corrected observations from raw totals; do not double count them.
- Check correlation coverage before attributing telemetry to a task revision,
  lifecycle, or worker. Do not infer model cost or token consumption: the current
  event schema has no dedicated fields for these measurements.

## Legacy and mixed directories

Older directories can contain `state.md`, `proof-ledger.yaml`, per-stage
`context.md`, `handoff.md`, `report.md`, plans, review findings, verification
records, delivery records, patches, and human answers. Some also contain
`history/checkpoints/` snapshots, `history/routes/` decisions, and
`history/timeline.md`.

These files are historical evidence, not requirements for current sessions.
Inspect the state, route records, and relevant snapshots when the compact JSON
records are absent. Identify this as a legacy analysis. Do not migrate files or
claim that legacy completion passed the current validator.

For mixed directories, use current JSON records for current recorded state.
Use older files only for the period or revision they establish. Surface
contradictions instead of blending them into an apparently complete history.

## What the directory does not guarantee

Current Factory persistence does not automatically archive full conversations,
every prompt, every tool call, raw terminal logs, earlier copies of all current
records, or the exact Factory skill version used. Related-session links are
references, not copied transcripts. Git commits preserve product source, not
necessarily the Factory runtime or instructions.

The report must distinguish unsupported conclusions from observed failures.
Recommend additional capture only when a concrete analytical question requires
it. Prefer compact decisions, stable references, and sanitized summaries over
full transcripts or duplicated state.
