---
name: codex-cli
description: "Use only when explicitly requested by another workflow or the human to execute one isolated Codex CLI task in a specified repository. Run Codex in an observable subagent, stream sanitized progress and user-facing response text, and perform one preflight and one attempt without fallback models."
---

# Codex CLI

Execute one observable Codex CLI task. Keep the root responsive; never expose
reasoning, raw protocol events, command output, or secrets.

## Input

Require the repository, complete prompt and output contract, model, reasoning
effort, sandbox, and delivery mode. Default reviews to `gpt-5.6-sol`, high
reasoning, ephemeral execution, the read-only sandbox, and `observable`
delivery.

## Orchestration

- From the root, spawn one named subagent for the task. Inside an existing
  dedicated factory or review subagent, run Codex there without nesting again.
- With `observable` delivery, send the parent an attributed update at preflight,
  meaningful phase or tool transitions, every 30 seconds while active, and
  completion or failure. Relay user-facing answer text as it arrives,
  coalescing only for readability.
- With `result-only` delivery, send no progress, heartbeat, tool, or text events
  to the parent. Return only the authoritative result or sanitized failure.

## Preflight

Once, confirm `codex` is on `PATH`, run `codex --version` and
`codex login status`, and confirm the repository is readable. On failure, stop;
do not install, authenticate, elevate access, or substitute a model.

## Invocation

Pass the complete prompt through stdin to:

```text
python3 <skill-dir>/scripts/stream_codex.py \
  --repository <repository> \
  --model gpt-5.6-sol \
  --reasoning-effort high \
  --sandbox read-only \
  --delivery observable
```

The wrapper runs one ephemeral `codex exec --json` attempt. In `observable`
mode, consume its JSONL continuously and relay:

- `status`: initialization, heartbeat, and completion
- `tool`: safe activity category only, never command or tool output
- `text`: user-facing Codex message fragments
- `result`: authoritative final response
- `error`: sanitized failure

In `result-only` mode, consume the stream locally and expose only `result` or
`error`. Use this mode when another subagent will synthesize the response and
intermediate output must remain isolated.

The wrapper stops after five minutes without a Codex event; heartbeats do not
reset that timer. Active tasks may run longer while events continue.

## Rules

- Give Codex the complete task and instruct it not to spawn agents.
- Never broaden the sandbox, bypass approvals, resume unrelated sessions, or
  permit edits unless the human explicitly authorizes a different contract.
- Treat empty output, nonzero exit, model error, access failure, or stall as a
  failed task. Make no retry or fallback.
- Sanitize prompts, progress, and results.

Return status, CLI version and model, scope, final response or failure, evidence
gaps, and residual risk. Do not invoke Claude, merge results, or perform the
task outside Codex.
