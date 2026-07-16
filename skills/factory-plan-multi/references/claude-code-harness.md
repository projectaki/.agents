# Claude Code Harness Adapter

Use this adapter when the main thread and coordinator run in Claude Code.

## Preflight

- Require nested subagents and enough concurrency for the main thread,
  coordinator, and two workers.
- Resolve the installed `$codex-cli` skill and wrapper before spawning.

Never launch `claude -p` or the Claude Agent SDK from inside Claude Code. Use a
native Claude subagent for the Claude candidate.

## Workers

Spawn both concurrently:

1. `claude-planner`
   - Use a native read-only Claude planning subagent.
   - Give it the canonical brief, repository instructions, and repository.
   - Require no edits, no nested agents, and one final candidate plan.

2. `codex-planner`
   - Use a Claude subagent as the isolated CLI owner.
   - Give it the canonical brief, repository, and an explicit instruction to use
     `$codex-cli` exactly once with high reasoning, the read-only sandbox,
     ephemeral execution, and `result-only` delivery.
   - Require it to return only the authoritative Codex result or sanitized
     failure envelope.

Do not rely on skills invoked in the parent conversation being present in a
fresh Claude subagent. Preload `$codex-cli` when the host supports a `skills`
field, or give the worker the resolved skill path and require it to read that
skill before invocation.
