---
name: factory-plan-multi
description: "Use only when the human explicitly requests multi-agent planning for a software change and supplies planning context plus a completed factory-test-scope packet. Isolate independent Codex and Claude planning in nested workers, synthesize their evidence, and return one implementation-ready plan without modifying the repository."
---

# Factory Plan Multi

Produce one implementation-ready plan from independent Codex and Claude
planning passes while keeping candidate plans and tool output out of the main
thread.

## Input

Require the requested change, repository or worktree, supplied context,
acceptance criteria, constraints, applicable instructions, and a current
`$factory-test-scope` packet. If the packet is missing or stale, or a missing
decision materially changes the implementation, return the specific blocker.

## Main-thread workflow

1. Resolve this skill directory and the current host harness.
2. Read [references/coordinator.md](references/coordinator.md) and the matching
   host reference:
   - Codex: [references/codex-harness.md](references/codex-harness.md)
   - Claude Code: [references/claude-code-harness.md](references/claude-code-harness.md)
3. Spawn exactly one `plan-multi-coordinator` subagent. Give it the complete
   input, repository, applicable instructions, coordinator reference, and
   matching host reference.
4. Do not spawn planner workers from the main thread. Do not ask the coordinator
   for progress messages, candidate plans, tool output, or intermediate notes.
5. Wait for the coordinator and return its final response without adding a
   second planning or synthesis pass.

The coordinator must own both planner workers and synthesis so only the merged
plan reaches the main thread. If the runtime cannot support the required nested
workers, return that limitation instead of falling back to direct fan-out.

## Safety

Do not edit files, implement the change, run write-capable planner tools, or
silently replace a failed provider. Do not invoke Claude CLI from inside a
Claude Code harness; use a native Claude subagent there.

## Output

Return exactly one synthesized plan or one explicit incomplete/blocker result.
A successful plan must retain the output contract of `$factory-plan` so it can
be approved and passed to `$factory-implement` unchanged.

Stop after the coordinator result.
