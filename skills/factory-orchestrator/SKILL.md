---
name: factory-orchestrator
description: "Run or resume a persisted Factory software-change task. Restore compact state, select the next guarded lifecycle, dispatch one independent worker, persist its result, and either return in supervised mode or continue automatically until a real stop condition."
---

# Factory Orchestrator

Run the smallest safe workflow. Keep routing, authority, and stop decisions in
the orchestrator. Keep product work in lifecycle workers.

## Continuation

Use `supervised` mode by default while Factory is being tuned:

- `supervised`: checkpoint one lifecycle result and return.
- `automatic`: continue until completion or a stop gate passes.

Use the same routing rules in both modes. Changing modes must not change task
scope, proof, or authority.

## Route

Use this core graph:

1. `INTAKE` — `factory-intake`
2. `TRIAGE` — `factory-triage`
3. `PLAN_ASSURANCE` — `factory-assure` only when triage requires it
4. `IMPLEMENTATION` — `factory-implement`
5. `CHANGE_ASSURANCE` — `factory-assure`
6. `DELIVERY` — `factory-draft-pr` only when the task requests a draft pull
   request
7. `COMPLETED`

Use `AWAITING_INPUT` and `CANCELLED` as terminal pauses. Route an assurance
failure back to its owner. Allow one automatic backward correction. A second
backward correction requires human input.

Use the route returned by the deterministic Factory checkpoint helper after
each result. Do not override a stop result. Treat worker recommendations as
evidence, not routing authority.

## Stop gate

Pause only when at least one condition is true:

- a material product decision has more than one valid answer
- required authority is absent
- accepted scope must expand
- existing user changes conflict with the task
- destructive, irreversible, production, or sensitive work lacks approval
- required evidence, credentials, or dependencies are inaccessible
- triage or implementation invalidates the accepted contract
- the risk class or approved change surface increases
- one automatic backward correction did not resolve the failure
- two attempts repeat the same blocker without a changed precondition
- two consecutive actor results make no material progress
- automatic mode reaches 30 minutes of active time

Do not pause for repository-discoverable facts, ordinary choices inside the
accepted scope, an expected red test, a correctable implementation defect, or
one justified retry after a changed precondition.

Every pause must state the exact decision, supported options, consequences, and
the lifecycle that will resume.

## Authority

Read authority from the accepted task contract. Carry it across lifecycles for
the same task revision and scope. Keep `edit`, `test`, `commit`, `push`, and
`draft_pull_request` separate. A scope or task revision change invalidates
authority until the contract explicitly restores it.

Require edit, test, and commit authority before implementation. Require push
and draft-pull-request authority before delivery. A local commit is not a
remote write.

## Worker tier

Classify impact, uncertainty, reasoning difficulty, proof difficulty, and input
gaps as low, medium, or high from current evidence.

- Use `fast-worker` when every signal is low.
- Use `standard-worker` when at least one signal is medium and none is high.
- Use `high-worker` when at least one signal is high.

Assess the possible damage and reversibility of this change. Do not use the
business importance of the affected feature as change impact. Planning alone
does not require a high-tier worker.

## Dispatch

Delegate each lifecycle to a fresh native worker. Use one implementer. Keep
plan and change assurance independent from the implementer.

Supply the selected skill, task contract, current assurance record, repository,
authority, safety limits, required result contract, worker tier, and optional
telemetry assignment. Workers do not route, change scope, or approve their own
exceptions.

## Persist and continue

Use `factory-handoff` to restore and persist `task.json`, `assurance.json`,
`report.md`, and one compact `history.jsonl` event. Checkpoint before returning,
when awaiting input, after the implementation commit, before and after a remote
write, and at a terminal result.

In supervised mode, return after the checkpoint. In automatic mode, run the
route helper and continue unless it returns a stop or terminal result.

Use `factory-telemetry` only for optional runtime observations. The
orchestrator owns run and actor events. Workers own operation spans. Telemetry
must never control routing or completion.

## Completion

Complete a local task when independent change assurance passes for the exact
clean committed revision. Complete a delivery task only after the requested
draft pull request is published and read back for that revision. Require every
active acceptance criterion and material risk to have current evidence or a
human-accepted exception.

Use ASD-STE100 Simplified Technical English for human text. Write published
text in the developer's first-person singular voice when it describes their
actions, decisions, ownership, or requests.
