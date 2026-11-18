---
name: adapter-codex
description: How to get each capability that the x skills name when you run in Codex. Read before any other step of /x:go in Codex.
disable-model-invocation: true
---

# Codex adapter

| Capability | In Codex |
| --- | --- |
| Background subagent | The subagent spawn tool. |
| Fresh subagent | Always pass `fork_turns: "none"`. The default, `all`, gives the subagent your whole conversation. |
| Read-only subagent | No option for it. Put "do not edit files" in the brief. |
| Worktree subagent | No option for it. Create the worktree with `git worktree add`, and give its path in the brief. |
| x-agent | No custom agent types. Use the default type, and start the brief with "Read `agents/x-agent.md` in the x plugin first", with the absolute path. |
| Strongest, second, and fast model | The `model` parameter. Strongest: leave it out, so the subagent runs on your model. Second: `gpt-6.1-terra`. |
| Other-vendor model | Claude, through the CLI. See "Calling it from another harness" in the **adapter-claude-code** skill. |
| Effort | The `reasoning_effort` parameter. |
| Todo list | The plan tool. |
| Ask the user | Ask in plain text. In `codex exec`, no one can answer, so choose, continue, and say what you chose. |
| Run a skill | Read the skill's `SKILL.md` and follow it. |
| Validate the plugin | No validator. Check the frontmatter and the links by hand. |
| Headless run | Copy the skills to load into `<working folder>/.agents/skills/`. Then run `codex exec` as "Calling it from another harness" says, as a background shell command. |
| Session transcript | `~/.codex/sessions/<yyyy>/<mm>/<dd>/rollout-<time>-<session id>.jsonl`. `codex exec` prints `session id: <id>` at the start of its output. |
| Project skill folder | `.agents/skills/` in the repository root |

## Calling it from another harness

Run it as a background shell command, and read only the end of the output file. Without `</dev/null`, it waits for input forever.

`codex exec --skip-git-repo-check -C <working folder> "<prompt>" </dev/null > <output file> 2>&1`

For a read-only run, add `-s read-only`. To choose a model, add `-m <model>`.
