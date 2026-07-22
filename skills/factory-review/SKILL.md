---
name: factory-review
description: "Use only when the human explicitly starts the review lifecycle with a subject or context to review. Run two independent parallel reviews through Codex CLI and Claude CLI, stream their progress, and merge their evidence without modifying the subject."
---

# Factory Review

Review the supplied subject through two independent CLI agents.

## Input

Read the complete subject, context, focus, criteria, repository or worktree, and
applicable instructions. If no focus is supplied, assess relevant correctness,
completeness, consistency, feasibility, risk, and regression concerns.

## Parallel reviews

Spawn exactly two subagents concurrently:

- `codex-reviewer`: use `$codex-cli` once with `gpt-5.6-sol`, high reasoning,
  and the read-only sandbox.
- `claude-reviewer`: use `$claude-cli` once with `claude-opus-4-8`, high
  effort, plan permission mode, and read-only tools.

Give both the same sanitized input, repository, review criteria, and output
contract. Require supported findings with severity, precise subject location,
evidence, impact, smallest safe recommendation, and confidence. Instruct each
subagent to use only its assigned CLI, not review directly, spawn agents, edit,
or inspect the other result.

Relay each subagent's attributed preflight, phase or tool updates, 30-second
heartbeats, user-facing response text, and completion or failure as they arrive.
Do not wait silently for either CLI. Each cell gets one attempt; do not retry or
substitute a model or CLI.

## Merge

After both finish or fail, discard unsupported claims, merge findings with the
same root cause, preserve attribution and disagreements, and keep distinct
failure modes separate. A failed or unavailable cell makes the review
`incomplete` and prevents approval.

## Output

Return:

- reviewed scope and criteria
- both cell statuses
- verdict: `approve`, `approve-with-findings`, `reject`, or `incomplete`
- numbered merged findings with severity, location, evidence, impact,
  recommendation, confidence, and contributing CLI
- disagreements, questions, evidence gaps, and residual risk

A no-findings result must state what each CLI inspected and what remains
uncertain. Do not fix findings or start another lifecycle.
