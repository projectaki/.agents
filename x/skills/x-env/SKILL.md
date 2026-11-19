---
name: x-env
description: Create task worktrees and start agent sessions in them, on this machine or on a Rex host such as the VPS, with records written for you. Use when the go-env skill creates a task, when go starts a visible session, or when the user asks for a task, a session, or x-env.
---

# x-env

x-env runs every task in its own git worktree and records every agent session that it starts. The records are written by x-env and the harness hooks, never by the agent. Do not write findings files.

## Install it first

Before the first x-env command in a session, run the `x-env` script of this plugin with `install`. The script is `tools/x-env/x-env` in the plugin folder, two folders above this skill's folder:

```
<this skill's folder>/../../tools/x-env/x-env install
```

It links `x-env` into `~/.local/bin` and adds a marked block to `~/.bashrc` and `~/.profile`. It does nothing when both are already done. If a permission check stops it, give the user the command to run once. After it, call `x-env` by name.

## Layout

```
~/work/<project>/
  repo/main/                      the clone; setup creates it once
  tasks/<task>/repo/              the task's worktree, on its own branch
  tasks/<task>/AGENTS.md          the task's instructions
  sessions/<task>/<nnn>-<name>/   the records of each session
```

Run a command inside `~/work/<project>`, or pass `--project <name>`. Inside a task folder, the task is known. Elsewhere, pass `--task <name>`.

## Commands

- `x-env setup <project> <owner/repo, URL, or path>`: create the project and clone the repository. Running it again is safe.
- `x-env task <name>`: create the task worktree on the branch `feature/<name>`, new from the default branch, or reopen it.
  - `--base <branch>`: work on an existing branch.
  - `--onto <branch> --branch <new>`: start a new branch at another branch, for stacked work.
- `x-env chief --prompt "<task text>"`: start the lead agent of the task in a new Rex tab. It runs `/x:go <task text>` on Claude Code.
- `x-env agent --agent claude|codex --name <name> --prompt "<prompt>"`: start a visible session in a new Rex tab. Without Rex, it runs headless and says so.
- `x-env run --headless --agent claude|codex --name <name> --prompt "<prompt>"`: start a session that no one can answer. It prints the session id and returns at once.
- `x-env wait <session id>`: wait until the session exits. It prints the path of the session's `last-turn.md` and exits with the session's exit code.
- `x-env delete <task>`: stop the task's running sessions, then remove its worktree. The branch and the records stay. It refuses when the worktree has uncommitted work. `--force` discards that work, so ask the user first.

Common options for sessions: `--model`, `--effort low|medium|high|xhigh|max`, and `--access auto|full`.

## Records

Each session folder holds:
- `session.json`: the launch: harness, model, access, mode, and the harness session id with its transcript path.
- `events.jsonl`: one line per event: `started`, `turn_started` (Claude only), `turn_end` with the turn number and duration, and `exited` with the exit code.
- `last-turn.md`: the agent's last message.
- `output.log`: the terminal output of a headless session.

To read what a session did, read `last-turn.md` first, then the transcript named in `session.json`.

## On another machine

Add `--host <Rex host>` before the command to run it on that machine. The host is a label from `rex hosts` or an address. That machine cannot see your current folder, so also pass `--project`, and `--task` for session commands, as in `x-env --host vps --project shop task fix-login`. Paths are resolved on that machine. A `chief` or `agent` started this way opens its Rex tab on that machine, where the user sees it through Rex. If x-env is missing there, run `<plugin folder>/tools/x-env/x-env install` on that machine first.
