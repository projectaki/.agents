# Factory record contract

Use JSON with the standard library. Do not require YAML.

## `task.json`

Require:

- `schema_version`: `1`
- `task_revision`: positive integer
- `status`: `aligned` or `needs_input`
- `repository`: absolute path to the active worktree
- `base_ref`: target Git reference, required before review; resolve its current
  commit without fetching. Use a branch reference when its movement matters.
  A pinned commit is appropriate only for an explicitly fixed comparison base.
- optional `repository_identity`: shared Git directory from task-root discovery
- optional `related_sessions`: objects with `reference` and `relationship` text
- `objective`: nonempty text
- `acceptance_criteria`: nonempty text list
- `scope`: objects named `included` and `excluded`, each a text list
- `authority`: booleans named `edit`, `test`, `commit`, `push`, and
  `draft_pull_request`
- `deliverable`: `local_commit` or `draft_pull_request`
- `continuation_mode`: `supervised` or `automatic`
- `open_decisions`: text list

## `assurance.json`

Require after triage:

- `schema_version`: `1`
- matching `task_revision`
- `risk_class`: `low`, `medium`, or `high`
- five `signals`: `impact`, `uncertainty`, `reasoning_difficulty`,
  `proof_difficulty`, and `input_gaps`
- `low_risk_gate`: `eligible` and every check defined by the validator
- `sensitive_change`: boolean
- `plan_assurance_required`: boolean
- `paths`, `risks`, `diff_groups`, `evidence`, `exceptions`, and `blockers` lists
- `base_revision` and `change_revision`: text or null; before review these must
  match the resolved target commit and current head
- `branch`: the exact reviewed branch, required before review
- `verdict`: `unverified`, `plan_approved`, `plan_rejected`, `pass`, `fail`, or
  `blocked`
- `routing`: booleans named `decision_required`, `scope_changed`,
  `risk_changed`, and `required_dependency_unavailable`

Use stable identifiers inside the assurance record. Keep human reports free of
internal identifiers.

## Acceptance evidence

Each `paths` entry names its required `behavior` and `evidence` identifiers.
Every acceptance criterion must match a path's behavior text. Additional paths
cover required failure behavior. The router validates this mapping before
requesting change assurance, delivery, or completion.

An evidence entry contains `id`, `proof` (a command, precise test reference, or
artifact link), `state` (`planned` or `executed`), `result` (`pending`, `pass`,
`fail`, or `blocked`), `revision`, and `base_revision`. Planned proof does not
count as executed proof. Keep detailed output in linked artifacts. The helper
checks references and revisions; it does not execute tests or verify the
contents of external links.

For example, a path and its executed evidence can be:

```json
{
  "paths": [{"id": "completion", "behavior": "Stale completion is rejected.", "evidence": ["completion-test"]}],
  "evidence": [{"id": "completion-test", "proof": "python3 -m unittest test_completion", "state": "executed", "result": "pass", "revision": "<head commit>", "base_revision": "<target commit>"}]
}
```

An exception has `id`, exact `behavior`, `residual_risk`, `approval` reference,
`change_revision`, and `base_revision`. Only the path naming its `exception`
identifier can use it. List failed executed evidence when available. An
exception cannot make planned evidence appear executed or cover another path.
Use existing authorization as its approval reference when it covers the exact
behavior and residual risk.

Reuse an executed result only after verifying that its covered source,
configuration, and dependencies remain unchanged. Set its current `revision`
and `base_revision`, preserve `carried_from`, and record the concrete check in
`reuse_reason`. Do not rerun unchanged checks without a reason. A rebase requires
inspection of changed dependencies and checks for the affected behavior.

Existing records remain readable. Records without these fields must acquire
current proof before review or completion; do not invent past execution.

## `history.jsonl`

Each line is one complete JSON object produced by `checkpoint.py`. The record
contains its sequence, timestamp, lifecycle, outcome, selected next lifecycle,
resume lifecycle when paused, task revision, continuation mode, worker facts,
Git facts, and hashes of current canonical files.

Checkpoint outcomes belong to their lifecycle:

| Lifecycle | Outcomes |
| --- | --- |
| INTAKE | `aligned`, `needs-input`, `blocked` |
| TRIAGE | `ready`, `needs-input`, `blocked` |
| PLAN_ASSURANCE | `approve`, `reject`, `needs-input`, `blocked` |
| IMPLEMENTATION | `complete`, `needs-input`, `blocked` |
| CHANGE_ASSURANCE | `pass`, `fail`, `needs-input`, `blocked` |
| DELIVERY | `published`, `needs-input`, `blocked` |
| AWAITING_INPUT | `resolved`, `needs-input`, `blocked` |
| COMPLETED | `complete`, `reopened` |
| CANCELLED | `cancelled` |

The helper stores outcomes in lowercase with underscores. For example, triage
uses `--outcome ready`; `complete` belongs to implementation or completion.
Evidence uses literal results such as `"result": "pass"`. Put explanations in
proof references or the report, not in the result field. Existing history is
not rewritten by submission validation.

The final valid line is current Factory state. Never edit or reorder an existing
line.

Completion entries retain a compact delivery summary and evidence references.
Use `--reason` to state the delivered behavior and result, not just “complete”.
The base, head, and task revision bind findings and decisions to their subject.
Use repeatable `--finding` JSON arguments containing `kind`, `summary`,
`revision`, and `evidence`. The allowed kinds are `missed_defect`,
`new_requirement`, `dependency_change`, and `accepted_risk`. Use repeatable
`--decision` arguments for compact decisions. A missed defect violated the
accepted behavior at its reviewed revision. The other kinds identify changed
requirements, changed dependencies, or a specifically accepted residual risk.

Supply `--worker-id` and `--active-seconds` when available. Active time excludes
waiting and gaps between sessions. Omit unknown values. Optional telemetry is
never required for a checkpoint or routing decision.
