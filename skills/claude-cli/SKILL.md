---
name: claude-cli
description: "Use only when explicitly requested by another workflow or the human to execute one isolated Claude CLI task in a specified repository with an explicit prompt, model, effort, permission mode, and output contract. Run Claude in an observable subagent, stream sanitized progress and answer text, and perform one preflight and one attempt without fallback models."
---

# Claude CLI

Execute exactly one observable Claude CLI task and return its result. Keep the
root responsive while Claude works; do not expose hidden reasoning or raw tool
output.

## Input

Require:

- repository or worktree path
- complete task prompt and output contract
- model and effort level
- permission mode and tool set
- delivery mode: `observable` or `result-only`

Default reviews to `claude-fable-5[1m]`, high effort, plan permission mode,
`Read,Grep,Glob,Bash`, no session persistence, and `observable` delivery. Do not
infer a different model or broaden permissions.

## Host orchestration

- If running in the root session, spawn one named subagent for this Claude task.
  Give it the repository, complete prompt, execution contract, and an explicit
  instruction to use this skill. The root relays its progress messages to the
  human through commentary and remains responsive to steering.
- If already running inside a dedicated factory or review subagent, execute
  Claude there. Do not create another nested agent.
- With `observable` delivery, the Claude-owning subagent sends its parent a
  concise update at preflight, each meaningful tool or phase transition, every
  30 seconds while active, and completion or failure. Stream user-facing answer
  text when it arrives, coalescing only for readability.
- With `result-only` delivery, send no progress, heartbeat, tool, or text events
  to the parent. Return only the authoritative result or sanitized failure.
- Never stream thinking blocks, hidden reasoning, raw protocol JSON, tool
  results, authentication details, or secrets.

## Preflight

Perform each check once inside the Claude-owning subagent:

1. Confirm `claude` is on `PATH`.
2. Run `claude --version`.
3. Run `claude auth status`, reporting only whether authentication succeeded.
4. Confirm the repository path is readable.
5. Confirm the process is not already running inside Claude Code. If
   `CLAUDECODE` is set, stop and require a native Claude subagent instead.

If a check fails because the CLI is missing, unauthenticated, sandboxed, or
access-controlled, stop. Do not install Claude, change authentication, request
elevated access, or substitute another model.

## Observable invocation

Run the bundled wrapper from the target repository and pass the complete prompt
through stdin:

```text
python3 <skill-dir>/scripts/stream_claude.py \
  --repository <repository> \
  --model 'claude-fable-5[1m]' \
  --effort high \
  --permission-mode plan \
  --tools 'Read,Grep,Glob,Bash' \
  --delivery observable
```

The wrapper invokes one `claude -p` process with `stream-json`, partial message
events, strict MCP configuration, Chrome disabled, and no session persistence.
It emits sanitized JSON lines:

- `status`: initialization, heartbeat, and completion milestones
- `tool`: a tool name and safe file/pattern context, never tool output
- `text`: user-facing Claude response fragments
- `result`: the complete final Claude response
- `error`: sanitized diagnostics

With `observable` delivery, consume output continuously and relay status/tool
updates promptly. Text fragments may be coalesced into readable chunks. With
`result-only` delivery, consume all intermediate events locally and expose only
`result` or `error`. Use the `result` event as the authoritative final response.

The wrapper terminates the attempt after five minutes without any Claude stream
event. Heartbeats do not reset that timer. An active review may run longer than
ten minutes while events continue.

## Safety and execution rules

- Make one ordinary CLI attempt after preflight.
- Give Claude the complete task; do not rely on hidden parent reasoning.
- Instruct Claude not to spawn nested agents.
- Never use `--dangerously-skip-permissions`, enable a fallback model, resume an
  unrelated session, or permit edits unless the human explicitly authorizes a
  different contract.
- Treat an empty final response, nonzero exit, model error, access failure, or
  stall cancellation as a failed task, not as a review finding.
- Sanitize prompts, progress, and results. Do not persist secrets, credentials,
  tokens, personal data, or sensitive production data.

## Output

Return:

- status: `completed`, `failed`, or `unavailable`
- CLI version and model used
- repository and task scope
- final Claude response when completed
- exit, stall, or access failure when not completed
- evidence gaps and residual risk

## Stop condition

Stop after one completed or failed invocation, or after a failed preflight.
Return the single-task result. Do not retry, invoke Codex, merge results, start
another lifecycle, or perform the requested task outside Claude.
