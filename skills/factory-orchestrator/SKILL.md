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

Text published or sent under the human's identity must read as if the human
wrote it. Use first-person singular voice for the human's actions, decisions,
opinions, ownership, and requests. Never refer to the human as `the author`,
`the developer`, `the requester`, `the user`, or `the human` in that text.
Never tell a reader to contact the human. State the human's request or position
directly. Do not invent `we`, `our`, or team authorship. Use collective voice
only when the human requests it or the canonical source text clearly has
collective authorship. Neutral technical facts do not need a first-person
pronoun.

Progress updates, questions, lifecycle reports, and final responses are
addressed to the human. Do not impersonate the human in those messages.

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
invocation IDs, the writer command, and a telemetry assignment to the worker. A
resumed invocation names the earlier run but gets a new identifier.

The orchestrator owns telemetry policy. Work skills do not depend on telemetry.
Add these observations to the applicable worker assignment:

- Intake: material operations, failures, retries, waits, and recovery.
- Context gathering: material research, unavailable sources, failures, retries,
  waits, and costly fallbacks.
- Replication: every attempt, environment startup, failure, retry, recovery,
  and wait. Keep one operation identity across retries.
- Analysis: material investigations, unavailable evidence, failures, retries,
  and recovery.
- Planning: material repository operations, failures, retries, recovery, and
  waits.
- Implementation: environment and Docker startup, builds, tests, static
  analysis, material operations, every failure, retry, recovery, interruption,
  wait, and material workspace change batch. Include the Git head, diff
  fingerprint, and changed file names when available.
- Review: material inspection or validation, unavailable checks, failures,
  retries, and recovery.
- Video evidence: browser and environment startup, authentication recovery,
  workflow attempts, failures, retries, recording, and waits.
- Verification: environment startup, every evidence-bearing check, failure,
  retry, recovery, interruption, and wait.
- Delivery: push and pull request operations, failures, retries, fallbacks, and
  read-back checks.

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

## Compose

The orchestrator owns lifecycle order and input composition. A work skill knows
only the semantic inputs that it receives.

1. Restore the current task contract and persisted step results through
   `factory-handoff`.
2. Select the next lifecycle from the route rules.
3. Read the selected work skill's declared input contract.
   Validate all work-skill contracts when they changed:

   ```bash
   python3 <skill-directory>/scripts/validate-step-contracts.py
   ```

4. Map persisted results and current workspace facts into those semantic inputs.
   Supply complete data, not only storage paths. Include provenance when it is
   necessary to validate revision or evidence freshness.
5. Supply required capabilities, mutation authority, safety limits, and human
   decisions.
6. Validate that every required input is present, current, and consistent. Route
   a missing input to its owner or enter `AWAITING_INPUT`.
7. Require the declared structured result, human summary, artifacts, side-effect
   account, and failure status.

For an active legacy task without an acceptance-proof record, derive one from
the accepted task contract and current persisted results before an assignment
requires it. Persist it through `factory-handoff`. Do not backfill a completed
legacy task.

Use these mappings:

- `INTAKE`: request, supplied artifacts, and human access.
- `CONTEXT_GATHERING`: task contract, repository, linked artifacts, and permitted
  sources.
- `REPLICATION`: bug report, environment, known steps, evidence, capabilities,
  and safety limits.
- `ANALYSIS`: task contract, evidence packet, and applicable reproduction result.
- `PLANNING`: task contract, evidence packet, impact analysis, paths, risks,
  acceptance-proof record, repository, and human decisions.
- `REVIEW`: bounded subject, focus, criteria, context, revision, and evidence.
- `IMPLEMENTATION`: approved plan, repository, acceptance criteria, decisions,
  paths, risks, acceptance-proof record, proof requirements, applicable
  reproduction result, and mutation authority.
- `VIDEO_EVIDENCE`: one visual workflow, identifiers, rationale, evidence
  workspace, environment, authentication, setup, cleanup, and tool capability.
- `VERIFICATION`: task contract, analysis, approved plan, change revision, diff,
  implementation result, change-assurance record, independent review,
  acceptance-proof record, applicable reproduction result, evidence, and check
  capabilities.
- `DELIVERY`: repository, branches, exact revision, publication authority,
  draft-state policy, task and scope, final behavior, diff, finalized assurance
  and proof records, material concerns, review findings, product gaps,
  publication eligibility verdict, and reviewer-accessible evidence links.

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

- Supply the skill, bounded objective, composed semantic inputs, capabilities,
  mutation authority, declared output contract, human-summary requirements, and
  optional telemetry assignment.
- For an assignment that publishes or sends text under the human's identity,
  require the human's first-person singular voice and prohibit third-person
  references to the human or unsupported collective voice.
- Do not duplicate the work skill's implementation rules in the assignment.
  Require its complete declared result.
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
2. Convert the returned human summary into the lifecycle `report.md`. Apply the
   shared human report pattern without changing the result's meaning.
3. Use `factory-handoff` to persist the structured result, `report.md`,
   artifacts, side-effect account, exit outcome, route reasoning, and applicable
   complete acceptance-proof and change-assurance records. Require handoff to
   persist those records before it creates the immutable snapshot.
4. Validate the persisted proof ledger and assurance record. Verify the complete
   checkpoint and immutable snapshot.
5. Commit the next lifecycle or pause state, then return control.

Worker recommendations are evidence, not routing commands. Keep internal IDs
and full mappings in agent records; keep `report.md` concise and plain.

Mark `COMPLETED` only when the final diff is fully accounted for, independent
review and final-revision verification pass, required exceptions are approved,
and a draft PR exists for that revision. The published PR body must exactly
match the validated delivery body and include complete plain-language
traceability from every assurance path and material concern to evidence.
Treat a missing row, required section, evidence link, verdict, or residual-risk
statement as delivery failure.
