# Orchestrator Model Tiers

This file is the provider-specific model policy for the abstract tiers defined by the orchestrator protocol.

| Abstract tier | Codex worker | Model and effort | Claude worker | Model and effort |
| --- | --- | --- | --- | --- |
| `standard` | `standard-worker` | `gpt-5.6-terra`, `medium` | `standard-worker` | `claude-sonnet-5`, `high` |
| `high_reasoning` | `high-reasoning-worker` | `gpt-5.6-sol`, `high` | `high-reasoning-worker` | `claude-opus-5`, `high` |

## Dispatch

1. The router selects only an abstract tier.
2. At the actor-dispatch boundary, select the worker profile for the active runtime from the table.
3. Supply the lifecycle role, bounded assignment, mutation authority, inputs, and output contract in the delegation.
4. Record the abstract tier, runtime, worker profile, concrete model, and effort in the active invocation and lifecycle handoff.

Do not use aliases or inherited models for tier-selected work. The effort labels are provider-specific values and are not equivalent across providers.

The primary orchestrator is not a tier-selected worker. Its defaults are:

- Codex: `gpt-5.6-sol`, `medium`
- Claude: `claude-opus-5`, `high`
