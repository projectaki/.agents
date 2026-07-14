---
name: claude-cli
description: "Use only when explicitly requested by another workflow or the human to execute one isolated non-interactive Claude CLI task in a specified repository, with an explicit prompt, model, effort, permission mode, and output contract; perform one preflight and one attempt without orchestration or fallback models."
disable-model-invocation: true
---

# Claude CLI

Execute exactly one Claude CLI task and return its result to the caller. Do not
coordinate multiple tasks or merge results.

## Input

Require:

- repository or worktree path
- complete task prompt and output contract
- model and effort level
- required permission mode and tool set

Default review invocations to `claude-fable-5[1m]`, high effort, plan permission
mode, read-oriented tools, and no session persistence. Do not infer a different
model or broaden permissions.

## Preflight

Perform each check once:

1. Confirm `claude` is on `PATH`.
2. Run `claude --version`.
3. Run `claude auth status`.
4. Confirm the repository path is readable.

If a check fails because the CLI is missing, unauthenticated, sandboxed, or
access-controlled, stop. Do not install Claude, change authentication, request
elevated access, or substitute another model automatically.

## Invocation

From the repository, pass the prompt through stdin and run one command shaped
like:

```text
claude \
  -p \
  --model 'claude-fable-5[1m]' \
  --effort high \
  --permission-mode plan \
  --tools 'Read,Grep,Glob,Bash' \
  --strict-mcp-config \
  --no-chrome \
  --no-session-persistence \
  --output-format text
```

Capture stdout as the final task result and stderr as diagnostics.

Never use `--dangerously-skip-permissions`, enable a fallback model, broaden the
tool set, resume an unrelated session, or allow the CLI task to edit files
unless the human explicitly supplies a different authorized contract.

## Execution Rules

- Make one ordinary CLI attempt after preflight.
- Give the CLI the complete task; do not rely on hidden parent-agent reasoning.
- Instruct the CLI not to spawn nested agents when independent execution is part
  of the caller's contract.
- Treat an empty response, nonzero exit, model error, or access failure as a
  failed cell, not as a finding or successful result.
- Sanitize prompts and outputs. Do not persist secrets, credentials, tokens,
  personal data, or sensitive production data.

## Output

Return:

- status: `completed`, `failed`, or `unavailable`
- CLI and model used
- repository and task scope
- final Claude response when completed
- exit or access failure when not completed
- evidence gaps and residual risk

## Stop Condition

Stop after one completed or failed invocation, or after a failed preflight.
Return the single-task result to the caller. Do not retry, invoke Codex, merge
results, start another lifecycle, or perform the requested task outside Claude.
