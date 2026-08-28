---
name: factory-telemetry
description: Record and analyze best-effort, noncanonical Factory runtime telemetry under the current task root. Use when a Factory run, actor, material tool operation, failure, retry, recovery, wait, interruption, resume, or external action must be timed or preserved for later process analysis without affecting lifecycle state, routing, checkpointing, or resume.
---

# Factory Telemetry

Record operational observations in `<task-root>/telemetry/events.jsonl`. Telemetry
is append-only, best effort, and noncanonical. Never read it to select a
lifecycle, validate a checkpoint, restore state, or decide whether work passed.
A telemetry failure never blocks Factory work.

## Record an event

Run the bundled writer:

```bash
python3 <skill-directory>/scripts/record-event.py \
  --event-type operation_failed \
  --run-id <run-id> \
  --lifecycle IMPLEMENTATION \
  --operation-id docker-start \
  --attempt 1 \
  --category environment_setup \
  --failure-class environment \
  --summary 'The Docker service did not become healthy.' \
  --best-effort
```

Pass `--task-root` only when the current workspace cannot resolve the intended
Factory task. The writer creates `telemetry/` lazily, locks the JSONL file,
writes one compact JSON object and newline, and never changes existing lines.

Use absolute UTC timestamps. The writer supplies `recorded_at` and defaults
`occurred_at` to the same instant. Supply `--occurred-at` when recording an
earlier observation. Keep `occurred_at` as the observed time and `recorded_at`
as the append time.

## Events

Use these event types:

- `run_started`, `run_finished`, `run_interrupted`, `run_resumed`
- `actor_dispatched`, `actor_completed`, `actor_interrupted`, `actor_replaced`
- `operation_started`, `operation_succeeded`, `operation_failed`,
  `operation_interrupted`
- `recovery_started`, `recovery_finished`
- `wait_started`, `wait_finished`
- `external_action_attempted`, `external_action_succeeded`,
  `external_action_failed`, `external_action_verified`
- `human_input_received`, `human_decision_recorded`
- `workspace_changed`, `artifact_changed`, `artifact_invalidated`
- `event_corrected`

Correlate related events with `run_id`. Use `operation_id` and `attempt` for an
operation. Use `retry_of` and `precondition_change` for a retry. A resumed run
gets a new `run_id` and names the earlier run with `resumes_run_id`.

An attempt greater than 1 must name `retry_of` and either `retry_reason` or
`precondition_change`. Use `retry_reason` when an unchanged retry is justified
by a transient failure.

Record every failed material operation, retry, recovery, interruption, human or
external wait, and external write. Also record service, Docker, database,
emulator, browser, build, test, lint, type, static-analysis, migration, and other
operations expected to take more than about 30 seconds. Do not record routine
file reads, short successful searches, every file save, or private reasoning.

Record `workspace_changed` after a material change batch, a human-directed edit,
or an orchestrator correction outside a worker result. Include the Git head,
diff fingerprint, and changed file names when available. Record material
artifact changes and invalidations. Do not emit one event for every file save.

Do not repeat a failed operation with unchanged preconditions unless the failure
can be transient. Record why the retry is justified and what changed.

## Safety

Never record secrets, credentials, environment values, private URLs, customer
data, raw sensitive output, or full commands that can contain them. Use a short
sanitized summary. Put useful sanitized output in `telemetry/artifacts/` and
reference it with `--evidence`.

Telemetry is not an actor result. Do not put telemetry counters in `state.md`,
copy telemetry into checkpoints, or make a lifecycle output depend on it. With
`--best-effort`, report a writer error to stderr and continue with exit code 0.

## Analyze telemetry

Run:

```bash
python3 <skill-directory>/scripts/summarize-events.py
```

The analyzer validates each line independently and rebuilds
`telemetry/summary.md`. It reports malformed lines, missing result events,
failures, retries, time by category, recorded run time, pause time, and
unobserved interruption gaps. A missing finish event produces a lower-bound
duration. A next-day gap is pause or unobserved time, never active work.

Treat the summary as an analytical view. `factory-learn` can use it with the
canonical history, but it remains optional and noncanonical.
