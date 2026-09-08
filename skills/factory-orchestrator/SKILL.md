---
name: factory-orchestrator
description: "Run or resume a persisted Factory software-change task. Select useful stages from current evidence, validate action prerequisites, dispatch bounded work, and preserve results with default runtime recording."
---

# Factory Orchestrator

Choose the smallest amount of work that establishes the requested result.
Keep scope, authority, routing, and stop decisions in the orchestrator.

## Guidance

At every new or resumed run, read
[`references/engineering-guidance.md`](references/engineering-guidance.md) in
full. Read applicable `AGENTS.md` and `CLAUDE.md` files in the target repository.
Supply their paths to workers and require them to read the applicable guidance.
Do not copy the full task history into each assignment.

## Select useful work

Stages are reusable responsibilities. They do not require a fixed sequence or
a separate worker for every responsibility. Select the next stage from the
accepted outcome, repository findings, risk, uncertainty, size, and dependencies.
Explain the selection in one concrete sentence.

| Current need | Stage and skill |
| --- | --- |
| Define or change the accepted outcome and authority | INTAKE: `factory-intake` |
| Resolve code, dependency, proof, or risk uncertainty | TRIAGE: `factory-triage` |
| Independently examine a consequential plan | PLAN_ASSURANCE: `factory-assure` |
| Implement understood work and its focused proof | IMPLEMENTATION: `factory-implement` |
| Independently verify the committed change | CHANGE_ASSURANCE: `factory-assure` |
| Publish an authorized draft pull request | DELIVERY: `factory-draft-pr` |
| Verify the requested deliverable is finished | COMPLETED |

Before classifying a request as small and low risk, inspect its relevant code
and dependencies. Record the findings in the assurance assessment. A short
request alone is insufficient evidence. If this assessment resolves the
necessary investigation, proceed from intake to implementation. A separate
triage assignment is unnecessary. Keep the original outcome and constraints
visible even when preparation takes only a few sentences.

Combine intake and brief investigation when useful. A worker can investigate
and implement in one assignment only after the implementation prerequisites
pass. Give uncertain work a bounded investigation first. Do not grant dependent
implementation authority while a required decision or plan review is unresolved.

Use plan assurance for sensitive behavior, high change impact, or a material
unresolved design choice. Resolve uncertainty through investigation. Reassess
risk when new evidence appears. Return to triage for an invalid assumption;
return to implementation for an understood defect. Do not reopen settled
choices merely because a new worker prefers another approach.

For large tasks, retain one short parent specification with shared constraints,
remaining behavior, and dependencies. Implement coherent parts in sequence.
Use implementation `in-progress` results between parts. Reuse valid investigation
and proof. Review the combined result against every parent requirement before
completion. Additional commits and bounded workers
are permitted when necessary; keep one active implementation owner. Do not
repeat intake for each part or create a separate delivery system.

## Validate and dispatch

Use `factory-handoff` to restore state and validate selected action prerequisites.
Use its `start-assignment.py` before a worker begins product work. Supply the
selected stage, worker identity, and routing reason. Use one stable run identity
through an automatic continuation. Start a new run after a supervised return or
resolved human pause. Preserve the returned assignment identity through result
submission. Apply the returned timeout to native worker waits; interrupt a
worker when the automatic execution allowance expires. The helper records
start time; it cannot terminate a native agent by itself.

Keep plan and change reviewers independent from the implementer. Reuse an
implementation worker while its context remains useful. Start a fresh worker
for independent review or when context has become too large or obsolete.

Give each worker the current contract, relevant findings, source references,
required result, authority, and proof references. Keep completed findings and
long output in referenced artifacts. Include a short project setup and test
command reference when available. Refresh it when its dependencies change.

Supply `factory-telemetry/scripts/run-check.py` as the timed check command for
material builds and tests. It preserves the command's exit status and saves a
sanitized execution receipt. Existing reliable receipts are reusable after
checking source, configuration, dependencies, and environment. Require a
concrete reason for each repeated check. Review source independently even when
execution results are reused.

Choose `fast-worker` for all-low signals, `standard-worker` for medium signals,
and `high-worker` when a signal is high. These classify work; identical model
configurations do not create a speed difference. Change models only after
measuring comparable tasks.

## Persist and continue

Use the handoff helper to publish prepared current documents and their result
as one recoverable checkpoint. Supply a stable result identity, expected prior
sequence, worker identity, and whether the assignment made material progress.
Propose the next useful stage with `--next-lifecycle` and `--route-reason` when
the default route does not fit. The helper validates prerequisites; it does not
require visiting every stage. Never override a stop result.

Use `supervised` mode by default. Return after one assignment result. An
assignment can cover brief preparation and implementation where prerequisites
permit. In `automatic` mode continue until completion or a real stop.

Pause for a material product decision, missing authority, scope growth,
conflicting existing user changes, inaccessible required proof, two unchanged
failed attempts, two results without material progress, an unsuccessful allowed
correction, or 30 minutes of active automatic execution. Preserve the existing
one-correction allowance. Repository-discoverable facts and ordinary choices
inside the accepted scope do not require human input. Increased assessed risk
requires reconsideration; ask for input only if a real authority, scope, or
product decision remains. Checkpoint before waiting for a person so waiting
does not count as assignment execution. Interrupted time is unknown until
supported by runtime evidence.

Basic telemetry recording is enabled by default at dispatch and checkpoint.
Recording failures must not block product work. Mention incomplete telemetry
once in the final report if `telemetry-warning.txt` exists or expected boundary
events are missing. Never reconstruct task authority or completion from telemetry.

## Completion

Require the current clean committed head and base, complete acceptance and
material-risk evidence, and a recorded independent review. A draft pull request
also requires publication and readback for that revision. Reopen authorized
follow-up work explicitly. Do not weaken accepted requirements to obtain a pass.
Keep the human report concise and current. Use ASD-STE100 Simplified Technical
English. Write published text in the developer's voice.
