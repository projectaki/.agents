# Factory record contract

Use JSON with the standard library. Do not require YAML.

## `task.json`

Require:

- `schema_version`: `1`
- `task_revision`: positive integer
- `status`: `aligned` or `needs_input`
- `repository`: absolute path
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
- `base_revision` and `change_revision`: text or null
- `verdict`: `unverified`, `plan_approved`, `plan_rejected`, `pass`, `fail`, or
  `blocked`
- `routing`: booleans named `decision_required`, `scope_changed`,
  `risk_changed`, and `required_dependency_unavailable`

Use stable identifiers inside the assurance record. Keep human reports free of
internal identifiers.

## `history.jsonl`

Each line is one complete JSON object produced by `checkpoint.py`. The record
contains its sequence, timestamp, lifecycle, outcome, selected next lifecycle,
resume lifecycle when paused, task revision, continuation mode, worker facts,
Git facts, and hashes of current canonical files.

The final valid line is current Factory state. Never edit or reorder an existing
line.
