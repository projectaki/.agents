---
name: factory-orchestrator
description: Route and run one lifecycle for a persisted software-change task. Use only when the human explicitly asks the primary thread to start, resume, recover, or advance Factory work; restore state, select one valid factory skill, checkpoint the result, and return control.
---

# Factory Orchestrator

Run exactly one lifecycle per invocation. Authorization does not carry to later
steps.

## Resume

1. Confirm this is the primary thread; workers only finish assignments.
2. Use `factory-handoff` to find or initialize the task in `~/.agents-db`.
3. Reconcile the request, lifecycle, artifacts, active actor, Git HEAD, and
   worktree.
4. On interruption or state conflict, checkpoint `AWAITING_INPUT`; do not guess.

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

## Dispatch

Delegate to a fresh native subagent. The primary thread only routes,
checkpoints, and reports.

- Supply the skill, bounded objective, mutation authority, canonical inputs,
  and required output.
- During `INTAKE`, relay the worker's questions to the human and resume intake
  with the answers.
- Use 1 implementer. Reviewers and verifiers must be independent.
- Start each assignment with `fast-worker`. Escalate only after a checkpointed
  reasoning-quality failure: `fast-worker` → `standard-worker` → `high-worker`.
- Route tool failures, access gaps, scope errors, and implementation defects;
  do not escalate them.
- Stop if the runtime cannot select the named profile.
- Resolve model and effort from the runtime profile. Before spawning, state the
  lifecycle, worker, model, and effort. Confirm only after spawning succeeds.

## Checkpoint

After the worker returns:

1. Check the skill output and exit conditions.
2. Use `factory-handoff` to persist the result, `report.md`, artifacts, exit
   outcome, and route reasoning.
3. Verify the checkpoint.
4. Commit the next lifecycle or pause state, then return control.

Worker recommendations are evidence, not routing commands. Keep internal IDs
and full mappings in agent records; keep `report.md` concise and plain.

Mark `COMPLETED` only when the final diff is fully accounted for, independent
review and final-revision verification pass, required exceptions are approved,
and a draft PR exists for that revision.
