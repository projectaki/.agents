---
name: codex-cli
description: "Use only when explicitly requested by another workflow or the human to execute one isolated non-interactive Codex CLI task in a specified repository, with an explicit prompt, model, reasoning effort, sandbox, and output contract; perform one preflight and one attempt without orchestration or fallback models."
disable-model-invocation: true
---

# Codex CLI

Execute exactly one Codex CLI task and return its result to the caller. Do not
coordinate multiple tasks or merge results.

## Input

Require:

- repository or worktree path
- complete task prompt and output contract
- model and reasoning effort
- required sandbox mode

Default review invocations to `gpt-5.6-sol`, high reasoning, an ephemeral
session, and the read-only sandbox. Do not infer a different model or broaden
permissions.

## Preflight

Perform each check once:

1. Confirm `codex` is on `PATH`.
2. Run `codex --version`.
3. Run `codex login status`.
4. Confirm the repository path is readable.

If a check fails because the CLI is missing, unauthenticated, sandboxed, or
access-controlled, stop. Do not install Codex, change authentication, request
elevated access, or substitute another model automatically.

## Invocation

Pass the prompt through stdin and run one command shaped like:

```text
codex exec \
  --ephemeral \
  --sandbox read-only \
  --color never \
  -C <repository> \
  -m gpt-5.6-sol \
  -c 'model_reasoning_effort="high"' \
  -
```

Use `--output-last-message <temporary-file>` when the caller needs a clean final
artifact. Keep diagnostic output separate from the returned result.

Never use `--dangerously-bypass-approvals-and-sandbox`, broaden the sandbox,
resume an unrelated session, or allow the CLI task to edit files unless the
human explicitly supplies a different authorized contract.

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
- final Codex response when completed
- exit or access failure when not completed
- evidence gaps and residual risk

## Stop Condition

Stop after one completed or failed invocation, or after a failed preflight.
Return the single-task result to the caller. Do not retry, invoke Claude, merge
results, start another lifecycle, or perform the requested task outside Codex.
