# Factory current state

Keep `state.md` as YAML front matter only. Use schema version 1:

```yaml
---
schema_version: 1
project_slug: example
branch_slug: feature--example
task_key: EXAMPLE-1
objective: Add the requested behavior.
task_revision: 1
status: lifecycle_active
current_lifecycle: IMPLEMENTATION
last_checkpointed_lifecycle: PLANNING
latest_handoff: planning/handoff.md
change_assurance_report: null
proof_ledger: proof-ledger.yaml
git_head: null
git_branch: feature/example
worktree_dirty: false
pending_transition: null
active_assignment: implementation-r1
active_attempt: 1
attempted_model_tiers: [standard]
stale_artifacts: []
checkpoint_sequence: 4
latest_snapshot: history/checkpoints/000004-planning/manifest.md
route_sequence: 4
latest_route_record: history/routes/000004-planning--implementation/decision.md
updated_at: 2026-08-28T10:00:00Z
---
```

Allowed statuses are `lifecycle_active`, `lifecycle_checkpointed`, and
`terminal`. Use only Factory orchestrator lifecycle names. Keep transitions and
stale artifacts structured. Put explanations in the current handoff.

Validate with:

```bash
python3 <factory-handoff-directory>/scripts/validate-state.py <task-root>/state.md
```

Legacy state without `schema_version` requires migration before the next route.
Use `--allow-legacy` only to inspect it without approving advancement.
