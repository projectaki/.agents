# Codex Harness Adapter

Use this adapter when the main thread and coordinator run in Codex.

## Preflight

- Require Codex subagent nesting depth of at least 2. The shape is main thread,
  coordinator, then two planner workers.
- Require enough concurrent threads for the main thread, coordinator, and two
  workers.
- Resolve the installed `$claude-cli` skill and wrapper before spawning.

If nesting is unavailable, return `incomplete`; do not spawn planners directly
from the main thread.

## Workers

Spawn both concurrently:

1. `codex-planner`
   - Use a native Codex subagent.
   - Give it the canonical brief and repository.
   - Require read-only planning, no edits, no nested agents, and one final
     candidate plan.

2. `claude-planner`
   - Use a Codex subagent as the isolated CLI owner.
   - Give it the canonical brief, repository, and an explicit instruction to use
     `$claude-cli` exactly once with high effort, plan permission mode,
     `Read,Grep,Glob,Bash`, no session persistence, and `result-only` delivery.
   - Require it to return only the authoritative Claude result or sanitized
     failure envelope.

Do not invoke `codex exec` for the Codex candidate. The native Codex worker is
already an isolated Codex planning context.
