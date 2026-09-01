---
name: factory-telemetry
description: "Record and summarize optional Factory runtime events without affecting canonical task state. Use for run, actor, operation, retry, recovery, wait, external-action, and performance observations."
---

# Factory Telemetry

Store sanitized append-only events in `<task-root>/telemetry/events.jsonl`.
Telemetry is optional and noncanonical. A telemetry failure must never block,
route, resume, or complete Factory work.

## Ownership

- The orchestrator records run, actor, human-input, and external-action events.
- Workers record their operation, retry, recovery, and wait spans.
- Record one start and one terminal event for each run, actor, and operation.
- Keep one operation identity across attempts. An attempt after the first must
  name a prior attempt and a retry reason or changed precondition.

Record material operations expected to take more than about 30 seconds. Record
every failure, retry, recovery, interruption, wait, external write, and material
workspace change. Do not record routine reads or private reasoning.

## Write

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

The summary reports active time, unobserved gaps, operation time by category,
failures, retries, incomplete spans, and semantic defects. It reports duplicate
terminal events, invalid retry sequences, unmatched spans, and impossible
recovery order. A next-day gap is never active work.
