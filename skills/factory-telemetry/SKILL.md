---
name: factory-telemetry
description: "Record and summarize Factory runtime events without affecting canonical task state. Use for run, actor, operation, retry, recovery, wait, external-action, and performance observations."
---

# Factory Telemetry

Store sanitized append-only events in `<task-root>/telemetry/events.jsonl`.
Basic recording is enabled by default through the handoff dispatch and
checkpoint helpers. Telemetry remains noncanonical. A recording failure must
never block, route, resume, or complete Factory work. Report incomplete
recording once; do not silently present missing observations as zero activity.

## Ownership

- The orchestrator records run, actor, human-input, and external-action events.
- Workers use the supplied timed check command for material builds and tests.
  Record additional retry, recovery, wait, and external-action spans when needed.
- Record one start and one terminal event for each run, actor, and operation.
  Do not duplicate boundary events already emitted by the handoff helpers.
- Keep one operation identity across attempts. An attempt after the first must
  name a prior attempt and a retry reason or changed precondition.

Record material operations expected to take more than about 30 seconds. Record
every failure, retry, recovery, interruption, wait, external write, and material
workspace change. Do not record routine reads or private reasoning.

## Timed checks

```bash
python3 <skill-directory>/scripts/run-check.py \
  --task-root <task-root> --cwd <repository> \
  --proof '<safe focused test description>' \
  --environment '<relevant safe environment description>' \
  --timeout <seconds> -- <command> <arguments>
```

The helper records start and finish events, enforces the timeout, preserves the
check exit status, and writes a compact receipt under `artifacts/checks/`.
It does not persist raw output or command arguments. Supply sanitized labels.
A receipt from a dirty tree needs source verification before reuse at a commit.

## Write additional events

```bash
python3 <skill-directory>/scripts/record-event.py \
  --event-type operation_failed \
  --run-id <run-id> \
  --operation-id <operation-id> \
  --attempt 1 \
  --category implementation \
  --failure-class product \
  --summary '<sanitized summary>' \
  --best-effort
```

Never record secrets, credentials, environment values, private URLs, customer
data, raw sensitive output, or full commands that can contain them.

## Summarize

```bash
python3 <skill-directory>/scripts/summarize-events.py --strict
```

The summary reports elapsed run time including waits, unobserved gaps, operation
time by category, failures, retries, incomplete spans, and semantic defects. It reports duplicate
terminal events, invalid retry sequences, unmatched spans, and impossible
recovery order. A next-day gap is never active work.
