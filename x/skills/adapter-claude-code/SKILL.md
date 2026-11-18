---
name: adapter-claude-code
description: How to get each capability that the x skills name when you run in Claude Code. Read before any other step of /x:go in Claude Code.
disable-model-invocation: true
---

# Claude Code adapter

| Capability | In Claude Code |
| --- | --- |
| Background subagent | The `Agent` tool. It runs in the background and notifies you when it finishes. |
| Fresh subagent | Every `Agent` spawn is fresh, except `subagent_type: "fork"`. |
| Read-only subagent | `subagent_type: "x:x-agent"`, with "do not edit files" in the brief. Do not use `Explore` for a review or a judge, because it reads excerpts, not whole files. |
| Worktree subagent | `isolation: "worktree"` |
| x-agent | `subagent_type: "x:x-agent"`. If the `Agent` tool does not list it, use `general-purpose`, and start the brief with "Read `agents/x-agent.md` in the x plugin first", with the absolute path. |
| Strongest, second, and fast model | `model: "opus"`, `model: "sonnet"`, `model: "haiku"` |
| Other-vendor model | Codex, through the CLI. See "Calling it from another harness" in the **adapter-codex** skill. |
| Effort | The `effort` parameter: `low`, `medium`, `high`, `xhigh`, or `max`. |
| Todo list | `TodoWrite` if the session has it. Otherwise keep the list in your reply. |
| Ask the user | `AskUserQuestion`. In `-p` mode, ask in plain text. |
| Run a skill | The `Skill` tool with `x:<name>`. If it refuses, read the skill's `SKILL.md` and follow it. |
| Validate the plugin | `claude plugin validate <plugin folder>` |

## Calling it from another harness

Run it as a background shell command in the working folder, and read only the end of the output file:

`claude -p "<prompt>" --model opus </dev/null > <output file> 2>&1`

For a read-only run, add `--permission-mode plan`. It refuses file edits, but it writes its plan to `~/.claude/plans/`.
