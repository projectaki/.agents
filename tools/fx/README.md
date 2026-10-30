# fx

`fx` prepares filesystem workspaces and starts interactive coding agents.
It uses Bash, Git, and Zellij. It does not schedule work. An initial assignment
can be supplied with `fx agent --prompt`.

## Load the command

From this checkout, run:

```bash
eval "$(/home/work/.agents/tools/fx/fx shell-init)"
```

Use the actual checkout path on another machine. Add that line to `.bashrc`
or `.zshrc` to load it in new terminals. Keep the whole `tools/fx` directory.
The shell integration adds it to `PATH` and defines the `fx` shell function.

The function changes the current directory after successful project setup.
Tasks open in Zellij. With `fx task <name> --no-attach`, the function changes
the current directory without opening Zellij. Without shell integration,
setup and tasks with `--no-attach` print the destination path.
All setup diagnostics go to standard error.

## Workflow

Connect to the server, or use a local terminal. Then run:

```bash
fx setup my-project owner/repository
fx task fix-login
fx agent claude
```

`fx task` creates or attaches to the Zellij session `my-project-fix-login`. A new session
opens its shell in the task directory. Enter the assignment in the agent's
interactive prompt. Open another terminal
or Zellij pane, enter the same task directory, and start another session:

```bash
cd ~/work/my-project/tasks/fix-login
fx agent codex -r h
```

Each launch creates a new session directory. It does not resume a previous
conversation. Exit the agent to return to the task shell.

## Commands

### `fx setup <project_name> [repository]`

Creates or reuses a project under `FX_ROOT`, which defaults to `~/work`.
Set `FX_ROOT` before setup to use another location:

```bash
export FX_ROOT="$HOME/projects"
```

Repository input accepts a GitHub `owner/repository` name, a Git URL, or a
local repository directory. GitHub names use the installed, authenticated
`gh` CLI. URLs and local paths use `git clone`.

The repository argument is optional. Without it, setup creates project
directories and memory. Run setup again with a repository to add the clone.
Task creation requires a clone with at least one commit.

Repeated setup preserves memory, context, branches, and uncommitted changes.
It rejects a different repository when a clone already exists.
It does not fetch, pull, reset, or clean an existing clone.

### `fx task <task_name> [--base <branch>] [--no-attach]`

Run inside the project or one of its tasks. Creates or reuses a task worktree
on `codex/<task_name>`. New branches start from the remote default branch
recorded by `origin/HEAD`, usually `origin/main`. The branch currently checked
out in the main clone does not affect this default.

Use `--base` to select a different starting branch:

```bash
fx task fix-login --base develop
fx task fix-login --base origin/release --no-attach
```

An explicit name resolves to a local branch first, then a remote-tracking
branch. For example, `develop` uses local `develop` if present, otherwise
`origin/develop`. Use `origin/develop` to select the fetched remote version.
Tags and commit identifiers are not accepted as branch names.
New task branches do not track the base branch as their upstream.

Multiple tasks can use the same base branch, even while that branch is checked
out in the main clone. Each task checks out its own `codex/<task_name>` branch.
For example, tasks `first` and `second` with `--base main` start at the same
commit but use `codex/first` and `codex/second`. Their later commits are independent.
Reopening the same task reuses its worktree. The tool does not force one task
branch into multiple worktrees.

Branch references use the locally available commits. Task creation does not
fetch. Run `git -C repo/main fetch origin` from the project directory to update
remote-tracking branches. If the recorded default branch is missing or unknown,
supply `--base`. The directory named `repo/main` can use any default branch name.

An existing task branch can be attached if it is not checked out elsewhere.
A conflicting checkout or worktree produces an error. Existing task files and
customized instructions are preserved. A switched task branch is not reset.
`--base` only applies when creating a new branch. Reopening an existing task or
reattaching an existing task branch preserves its history and reports that the
base option was not applied.

After preparing the worktree, the command creates or attaches to a Zellij
session named `<project_name>-<task_name>`. From inside Zellij, it switches sessions
instead of nesting another client. If already in that session, it stays there.
Existing sessions retain their panes and working directories. Detaching returns
to the original terminal and its original directory. The task session stays alive.

The project prefix lets different projects reuse a task name. Zellij session
names are shared by the operating-system account, so the combined name must
remain unique. A manually created session with the same combined name is reused.

Use `--no-attach` to prepare a task without Zellij, including from scripts.
Zellij must be installed for the default command. If attaching fails, the
worktree and context remain available. Rerun the command to retry.
Reload shell integration in already-open terminals after upgrading this behavior.

If a terminal appears stuck after `Task ready`, an old shell function may be
capturing Zellij's screen output. The command rejects captured output when
started from an interactive terminal and gives a reload instruction.
To recover an already-stuck terminal, open another terminal and run:

```bash
source ~/.bashrc
cd ~/work/my-project
fx task fix-login
```

Use the actual project and task names. In Zsh, reload `.zshrc` instead.
This attaches to the existing task session without resetting its worktree.
Scripts that capture a task path must use `--no-attach`.

Project and task names start with a letter or digit. Remaining characters
can be letters, digits, underscores, or hyphens.
Run setup and task creation sequentially. Parallel agent launches are supported.

### `fx agent <agent> [-r l|m|h] [--prompt <text>]`

Run inside a task or its worktree. The agent starts in the task directory.
The supported adapters are:

| Agent | Model | Reasoning setting |
| --- | --- | --- |
| `codex` | `gpt-6.1-sol` | `model_reasoning_effort` |
| `claude` | `claude-opus-5-5` | `--effort` |

`-r l` selects low, `-r m` selects medium, and `-r h` selects high.
Omitting the flag selects medium. Other values and extra arguments are rejected.
The launcher does not substitute a different model if access fails.

Without `--prompt`, the agent waits for an interactive assignment. Supply it
to start work immediately in the interactive session:

```bash
fx agent codex -r h --prompt 'Review the current changes. Write findings without editing source.'
fx agent claude --prompt 'Investigate the failing login test.'
```

An agent can open another agent in a new Zellij tab:

```bash
zellij action new-tab --name review --cwd "$PWD" -- \
  fx agent codex -r h --prompt 'Review the current changes without editing source.'
```

The launcher saves the exact initial text in the session's `initial_prompt.md`
and passes it as a user prompt. It does not add it to the system instructions.
Quote the text as one shell argument. Single quotes keep shell substitutions
literal. Empty assignments and repeated `--prompt` flags are rejected.
`--prompt` and `-r` can appear in either order. This flag does not select a
background or non-interactive execution mode; use a terminal or a Zellij tab.

Install and authenticate each agent CLI separately. Claude Opus 5.5 requires
Claude Code 2.1.280 or later. The Claude adapter removes the inherited
`CLAUDE_CODE_EFFORT_LEVEL` variable for its child process so it cannot override
the requested effort. It does not change the parent shell environment.

Codex receives session instructions through its `developer_instructions`
configuration setting. This overrides that setting for this session only.
Claude receives an appended system prompt file. A user prompt is passed only
when `--prompt` is supplied.
Both preserve their normal permission checks and user configuration otherwise.

## Files and context

```text
my-project/
├── .fx-project
├── project_memory.md
├── project_context/
├── repo/main/
└── tasks/fix-login/
    ├── AGENTS.md
    ├── repo/
    └── context/session-XXXXXXXX/
        ├── instructions.md
        ├── findings.md
        └── launch.txt
```

`AGENTS.md` contains editable task rules. Add `task.md` if a durable task
description is useful. The launcher creates session instructions with exact
paths and a findings file. It records the selected agent, model, and reasoning
in `launch.txt`. Session files remain available after an agent exits or fails.

Agents are instructed to read relevant context and update their own findings
after meaningful work. The tool creates the files and supplies the instructions;
it cannot guarantee that a model follows them or that its findings are correct.

Only the task and `project_context` are supplied as working directories.
Project memory remains at the project root. Writing it may require the agent's
normal permission approval. The launcher does not grant the entire project
directory just to make that file writable.

Assign one source writer per task and one editor of shared project memory or
context at a time. These are manual rules, not enforced locks. The directories
do not enforce read isolation. For independent investigations, provide the same
starting context, stop source edits, and instruct agents to avoid other session
findings until all investigators finish.

## Checks

Tests use Python's standard library, temporary local Git repositories, and
fake agent and Zellij executables. They make no model requests or network calls.

```bash
python3 -m unittest discover -s tools/fx/tests -v
bash -n tools/fx/fx tools/fx/agents/claude tools/fx/agents/codex
```

## Agent adapters

Each executable in `agents/` registers an agent under its filename.
The main command does not contain agent-specific branches.
An adapter supports `check` to verify its CLI exists and
`launch <project> <task> <session> <reasoning> [prompt]` to start it.
The main command sets the working directory to the task before launch.
Keep model defaults and CLI-specific configuration inside the adapter.

## CLI references

- [Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference)
- [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
- [Claude CLI arguments](https://code.claude.com/docs/en/cli-reference)
- [Claude models and effort](https://code.claude.com/docs/en/model-config)
- [Zellij session commands](https://zellij.dev/documentation/commands)
- [Zellij session switching](https://zellij.dev/documentation/cli-actions#switch-session)
