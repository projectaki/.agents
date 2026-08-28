---
name: factory-orchestrator
description: Route and run one lifecycle for a persisted software-change task. Use only when the human explicitly asks the primary thread to start, resume, recover, or advance Factory work; restore state, select one valid factory skill, checkpoint the result, and return control.
---

# Factory Orchestrator

Run exactly one lifecycle per invocation. Authorization does not carry to later
steps.

## Human communication

Use ASD-STE100 Simplified Technical English for every human-facing progress
update, question, report, checkpoint summary, and final response. Use short
sentences and the active voice. Define each term when first used. Do not use an
internal identifier without its plain-language meaning. Rewrite unclear or
noncompliant text before sending it.

Include these requirements in every worker assignment that can produce
human-facing text. Check and rewrite returned worker text before relaying it to
the human. Keep exact identifiers and machine-oriented detail in agent records.

## Resume

1. Confirm this is the primary thread; workers only finish assignments.
2. Use `factory-handoff` to find or initialize the task in `~/.agents-db`.
3. Reconcile the request, lifecycle, artifacts, active actor, Git HEAD, and
   worktree.
4. On interruption or state conflict, checkpoint `AWAITING_INPUT`; do not guess.

## Telemetry

When `factory-telemetry` is available, emit best-effort noncanonical events for
the orchestrator run, actor dispatch and result, interruptions, resumptions,
material operations, failures, retries, recovery, waits, and external actions.
Also record material workspace or artifact changes made between actor results.
Create a new `run_id` for each invocation and pass it, the assignment and
invocation IDs, and the writer command to the worker. A resumed invocation names
the earlier run but gets a new identifier.

Telemetry is optional. Never read it for routing or resume, include it in a
checkpoint, validate it as a lifecycle gate, or fail work because it cannot be
written. Canonical state and telemetry share a task root but have no state
dependency.

## Route

Choose the earliest missing or stale prerequisite, otherwise the next step:

1. `INTAKE` — `factory-intake`
2. `CONTEXT_GATHERING` — `factory-context`
3. `REPLICATION` — `factory-replicate` for bugs
4. `ANALYSIS` — `factory-analysis`, including test scope
5. `PLANNING` — `factory-plan`
6. `REVIEW` — `factory-review` when the plan needs independent review
7. `IMPLEMENTATION` — `factory-implement`
8. `REVIEW` — `factory-review`, including final-diff regression analysis
9. `VIDEO_EVIDENCE` — `factory-video-evidence` only when review shows automation
   cannot prove a required visual behavior
10. `VERIFICATION` — `factory-verify`
11. `DELIVERY` — `factory-draft-pr`
12. `COMPLETED`

Route failures to the earliest lifecycle that owns them. Route missing
authority, required input, unavailable dependencies, or ambiguity to
`AWAITING_INPUT`. Use `CANCELLED` only on explicit cancellation. Mark downstream
artifacts stale when inputs change; later artifacts never excuse a prerequisite.

## Assess

Before every dispatch, the orchestrator selects the lowest safe worker tier from
current canonical evidence. Reassess from zero for each lifecycle; a higher tier
does not carry forward.

Evaluate:

- impact: consequence, reversibility, and blast radius
- uncertainty: evidence quality, conflicts, assumptions, and material unknowns
- reasoning difficulty: novelty, coupled decisions, and architectural reach
- proof difficulty: how directly the result can be tested or inspected
- input gaps: missing, stale, incomplete, or unapproved required artifacts

Classify each signal as `low`, `medium`, or `high`. Do not average signals or let
low signals cancel a high one. Missing evidence belongs to the earliest lifecycle
that can obtain it, or `AWAITING_INPUT` when human or external input is required;
a stronger worker does not replace missing evidence.

Select:

- `fast-worker` when all signals are low. Prefer it for bounded implementation of
  a complete approved plan and for procedural delivery.
- `standard-worker` when any signal is medium and no high-tier condition applies.
- `high-worker` for high reasoning difficulty; cross-system architectural
  judgment; plan synthesis; or high-impact work combined with material
  uncertainty or difficult proof. Security, authorization, sensitive data,
  destructive migrations, concurrency, public contracts, and irreversible
  external effects require explicit high-tier consideration, not automatic
  inheritance by every later lifecycle.

Analysis, planning, review, and verification are sensitive to uncertainty,
reasoning difficulty, and proof difficulty. Implementation is usually fast when
the approved plan has already resolved those concerns. Select review and
verification tiers independently from the implementer tier.

Persist the signals, selected tier, concise evidence-backed rationale, and
assignment-specific escalation triggers. For a replacement attempt in the same
lifecycle, persist the new assessment in the handoff and checkpoint rather than
creating a self-route.

## Dispatch

Delegate to a fresh native subagent. The primary thread only routes,
checkpoints, and reports.

- Supply the skill, bounded objective, mutation authority, canonical inputs,
  required output, and optional telemetry context.
- For `DELIVERY`, explicitly require the PR sections `Task`, `What changed`,
  `Concerns raised during analysis`, `Regression assurance`, and `Gaps`.
  Require every assurance path and material concern to map to a plain-language
  regression row with affected surface, evidence, verdict, and residual risk or
  waiver. Require published-body read-back validation. Do not expect the worker
  to rediscover these requirements from earlier artifacts.
- During `INTAKE`, relay the worker's questions to the human and resume intake
  with the answers.
- Use 1 implementer. Reviewers and verifiers must be independent.
- Workers return bounded evidence. They do not select or recommend tiers, assess
  their own sufficiency, route work, or decide escalation.
- A worker stops and reports facts when continuing would exceed its assignment
  or authority. The orchestrator classifies the result and decides whether to
  accept it, replace the attempt, route backward, or enter `AWAITING_INPUT`.
- After each run, the orchestrator checks the evidence and exit conditions. On a
  checkpointed reasoning-quality failure, it may escalate exactly one tier:
  `fast-worker` → `standard-worker` → `high-worker`.
- Route missing information, tool failures, access gaps, scope changes, invalid
  prerequisites, and ordinary implementation defects to their owning lifecycle;
  do not treat them as model-tier failures.
- Stop if the runtime cannot select the named profile.
- Resolve model and effort from the runtime profile. Before spawning, state the
  lifecycle, worker, model, and effort. Confirm only after spawning succeeds.

## Checkpoint

After the worker returns:

1. Check the skill output and exit conditions.
2. Use `factory-handoff` to persist the result, `report.md`, artifacts, exit
   outcome, and route reasoning. Apply its shared human report pattern.
3. Validate the canonical proof ledger and verify the checkpoint.
4. Commit the next lifecycle or pause state, then return control.

Worker recommendations are evidence, not routing commands. Keep internal IDs
and full mappings in agent records; keep `report.md` concise and plain.

Mark `COMPLETED` only when the final diff is fully accounted for, independent
review and final-revision verification pass, required exceptions are approved,
and a draft PR exists for that revision. The published PR body must exactly
match the validated delivery body and include complete plain-language
traceability from every assurance path and material concern to evidence.
Treat a missing row, required section, evidence link, verdict, or residual-risk
statement as delivery failure.
