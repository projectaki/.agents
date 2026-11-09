# fx

`fx` prepares filesystem workspaces and starts interactive coding agents.
It uses Bash, Git, Zellij, and Python 3.9 or later. An initial assignment
can be supplied with `fx agent --prompt`.
Groups run independent investigations without interactive input, then start one interactive synthesis.
The sentry command can repeat diagnostic checks. Individual agent launches remain interactive.

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
```

`fx task` creates or attaches to the Zellij session `my-project-fix-login`.
In a new session, the first terminal starts the task orchestrator. Choose
Claude or Codex at the prompt, then give it the assignment. Exit the
orchestrator to open the task shell. Run `fx orchestrator` there to start
a fresh orchestrator in the same terminal.

You can also open another terminal or Zellij pane, enter the task directory,
and start an assigned agent directly:

```bash
cd ~/work/my-project/tasks/fix-login
fx agent codex --name review-login -r h
```

Each launch requires a session name and creates a new session directory.
Omit `--name` to enter the name at an interactive terminal prompt.
It does not resume a previous conversation. Exit the agent to return to the task shell.

## Record task checks

From a task directory or its worktree, run:

```bash
fx task check -- ./scripts/test-backend
fx task check status
```

The check runs once from the repository root. It writes standard output and
standard error to a log and prints the log path. It returns the command's exit
code or termination signal. Use a project script to set up dependencies and
stop a batch when a check fails. Keep secrets out of command arguments and logs.

fx gives agents instructions to associate checks with their session.
Use `--session DIR` to select a session explicitly. A response capture saves the
session's completed check records. The next reviewer can open that snapshot
from the starting context. Manual checks without a session appear in task status.

Use `--heavy` to wait for a lock shared by checks that opt in under the same host
user account. The record reports lock wait separately from execution.
Use `--tmp-dir DIR` with a disk-backed directory outside the repository.
Fx creates a private temporary directory there, sets `TMPDIR` for the command,
and removes the directory on exit. The command must use `TMPDIR` for this setting
to affect its build.

Status lists outcomes separately from source freshness. A current result has the
same Git revision and working file fingerprint before the check, after the check,
and now. Ignored files and external dependencies need separate setup evidence.

## Review a GitHub pull request

Run from the fx project directory or from a Git clone. From the project
directory, fx uses the clone in `repo/main`. The clone's `origin` must point to
the GitHub repository that owns the pull request. Authenticate the GitHub CLI
first.

```bash
fx pr review 123
fx pr review 123 --agent claude:h --agent codex:h
```

The command opens a review tab in a background Zellij session. It prints the
workspace path and a `zellij attach` command for when you want to join. The
default tab starts Claude Opus 5.5 with high reasoning and assigns both
`x-code-review` and `x-ensure-quality`.

Use `--agent` to select one or more group members. The `--interactive` and
`--synthesis-agent` options also select group mode, with Claude as the only
member if you omit `--agent`. Review accepts the other launch options from
`fx agent group`. Use `--prompt` to add a review focus. Relative `--from`
paths start in the review workspace.

Fx checks out the pull request head in a separate worktree and gives the
reviewer the exact target commit to use for comparison. Reviews live in
`reviews/pr-<number>/<revision>/` under the fx project. For a standalone
clone, they live under `fx/reviews/` in its Git directory. A change to either
commit creates a separate workspace. A repeat for the same commits reuses
the workspace and opens another review tab if the worktree is clean.

## Analyze a task

Run a retrospective from the project directory:

```bash
fx task analyze fix-login
fx task analyze fix-login --agent claude -r h
```

Inside a task or its source directory, omit the task name:

```bash
fx task analyze
fx task analyze --new-tab
```

The command starts an interactive analysis session. The default provider is
`codex`, configured in `default-analyze-agent`. Reasoning defaults to high.
`--new-tab` requires Zellij. The command analyzes an existing task. It does not
create a task, fetch source, or resume implementation. `analyze` is a reserved
task action name. Task actions register through executables in `task-commands/`.

Each run saves an evidence inventory and its report in a new numbered directory
under `context/analyses/`. The complete report goes in `findings.md` and the
normal captured final responses. Earlier reports remain available for comparison.
The inventory streams each evidence file with bounded memory. It records size,
line count, modification time, and a SHA-256 content hash. It records read errors
and skips symbolic links, source files under `repo/`, and prior analysis sessions.
The analyst inspects relevant source and instructions separately.

The assignment covers all recorded sessions, provider events, planning,
implementation, review groups, comparisons, fixes, tests, and delivery. It asks
for detailed event sequences and exact evidence references. Later discoveries
must be traced through earlier planning and review decisions. It also covers
memory failures, context limits, crashes, retries, recovery, lost findings, and
instruction conflicts. Recommendations name a concrete project instruction,
skill, or helper, plus a way to check whether the change works.

This is an analysis assignment. It does not apply recommendations or edit
source, project instructions, shared context, or original evidence. Agents use
their normal CLI permissions; the launcher does not enforce a filesystem sandbox.
Large logs must be read in bounded sections. The report must list unread files
and ranges when the agent cannot finish. The inventory is not a frozen copy.
Changes during or after inventory limit historical certainty. Include linked
records from the retired Factory workflow only when they identify this task.
The command does not search unrelated chat archives or create missing history.
It does not automatically combine reports into cross-task statistics.

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

### `fx task <task_name> [--base <branch>] [--onto <branch>] [--no-attach]`

Run inside the project or one of its tasks. A worktree is a separate Git
checkout that shares repository history.

Use `--base` without `--onto` to check out a specific branch in the task worktree:

```bash
fx task export-review --base feature/export
fx task export-review --base origin/feature/export --no-attach
```

The task checks out `feature/export` itself. It does not create
`feature/export-review` or substitute the selected branch's upstream commits.
An upstream is the branch Git uses by default for pull and for ahead/behind
comparisons.

An existing local branch keeps its commits and upstream configuration.
Selecting it by its local name works without fetching. If no local branch
matches, fx fetches `origin` and looks for the remote branch. An explicit remote
prefix such as `upstream/feature/export` selects that remote instead.
A remote-only branch gets a local branch with the same name, which tracks the
selected remote branch. For example, `origin/feature/export` creates local
`feature/export`. If that local branch already exists, fx uses its current
commits and preserves its upstream. It does not pull, merge, rebase, or reset it.

If a requested local name does not exist after fetching, fx creates that branch
from the fetched default recorded by `origin/HEAD`. The new branch has no
upstream and is not pushed. A missing remote-prefixed name produces an error.
Tags and commit identifiers are not accepted. A failed fetch stops the command.

An explicit `--base` takes priority over an existing task branch. Reopening a
task with a different branch switches its worktree to that branch. The old
branch and its commits remain available. Switching requires no uncommitted or
untracked files. Git also rejects a switch that would overwrite ignored files.
Save local changes before switching. Reopening on the same branch preserves
local files.

Use `--onto` to start a new task branch from an existing branch. For example,
if `feature/export` has an open pull request, create a branch for work that
depends on it:

```bash
fx task export-validation --base feature/export-validation --onto feature/export
```

With `--onto`, `--base` names the new branch. If you omit `--base`, fx uses
`feature/<task_name>`. Fx fetches `origin` to check that the new branch name is
available. A start branch name without a remote prefix selects the local branch
when it exists and otherwise selects the branch on `origin`. Use a prefix such
as `origin/feature/export` to select the fetched branch on that remote.

The new branch has no upstream. To stack the pull request, select
`feature/export` as its base when you open it. To reopen the task, omit
`--onto`. Fx rejects `--onto` if the task worktree or destination branch already
exists.

Git permits a branch in only one worktree at a time. If the selected branch is
checked out in the main clone or another task, fx reports an error. It does not
force a second checkout or move the other worktree. Use a separate local branch
if you need an independent checkout of the same commits.

Without `--base` or `--onto`, an existing task keeps its current branch and
files without fetching. For a task without a worktree, fx looks for existing
branches named `feature/<task_name>`, `<task_name>`, and `codex/<task_name>`,
in that order.
If none exists, it creates `feature/<task_name>` from the fetched default branch
and tracks that remote branch. The branch currently checked out in the main
clone does not affect this default. If `origin/HEAD` is missing, fx attempts to
discover the default from `origin`. The directory named `repo/main` can use any
default branch name.

All checked-out branch names work with `fx agent`. Existing task files and
customized instructions are preserved.

Task creation copies existing Git-ignored files from the project's `repo/main`
clone into the task worktree. It also copies existing untracked files selected
by `.worktreeinclude` in the root of that clone. This file uses Git ignore
pattern syntax: one pattern per line, with `#` comments and `!` exclusions.
Its patterns select additional files; they do not exclude Git-ignored files.
Tracked files use the task branch's committed versions.

Copies preserve relative paths and file permissions, including nested files.
All ignored files are eligible, including local configuration, dependencies,
and build output. Put needed local files in the main clone before creating a
task. Git cloning does not retrieve these local files from another checkout.

Reopening a task copies missing files as well. It never overwrites an existing
task file or link. To fill missing files without attaching to Zellij:

```bash
fx task fix-login --no-attach
```

Files tracked in the task are never copied, even when deleted locally.
Source symbolic links are skipped. `.worktreeinclude` must be a regular file.
A symbolic link in a missing file's destination directory path causes an error.
Copy failures preserve the worktree and existing files. Rerun the task command
after correcting the problem. Files are independent copies, so later changes
in the main clone do not update existing task files.

After preparing the worktree, the command creates or attaches to a Zellij
session named `<project_name>-<task_name>`. From inside Zellij, it switches sessions
instead of nesting another client. A new session uses a layout with the tab bar,
one terminal, and the status bar. The terminal prints its directory, repository
path, Zellij session name, latest commit, and Git status before starting the
orchestrator. When the orchestrator exits or fails to start, the terminal opens
the interactive shell selected by `SHELL` (Bash when unset). Git status includes
the branch, upstream comparison, and local changes. The summary reads the
current worktree when the terminal starts. The terminal reports Git errors and
continues startup.

If already in that session, the command stays there.
Existing sessions retain their panes and working directories. Detaching returns
to the original terminal and its original directory. The task session stays alive.
Reattaching does not restart the terminal or print a new startup summary.
The `--no-attach` option prints only the task path to standard output.

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

### `fx orchestrator`

Run from the task directory or its source worktree. Fx starts a fresh
interactive Claude or Codex session in the current terminal, with the task
directory as its working directory. To choose a provider in advance, export
`FX_ORCHESTRATOR_AGENT=claude` or `FX_ORCHESTRATOR_AGENT=codex`. If the variable
is empty or unset, fx prompts for a provider. Each provider uses its normal
model and permission settings.

The orchestrator receives its role, task paths, and the path to this reference.
It passes `--new-tab` to `fx agent` to launch assigned agents in separate Zellij
tabs. Fx skips its session directory, context capture, and event recording for
the orchestrator. Assigned agents still use the normal `fx agent` workflow.

### `fx delete <task_name> [--force]`

Deletes the named task directory, including its context and captured responses.
Removes its Git worktree registration and deletes the Zellij session named
`<project_name>-<task_name>`. A running session is stopped. An exited session's
saved state is deleted. Git branches and committed work on those branches remain.

Run from the project directory in a terminal outside the target Zellij session:

```bash
cd ~/work/my-project
fx delete fix-login
```

Uncommitted changes, untracked files, ignored files such as local settings, and
a detached checkout require `--force`:

```bash
fx delete fix-login --force
```

This discards those files and any worktree state from an unfinished rebase.
Detached commits are not saved to a new branch. Save any work you need first.
Task context files are deleted even without `--force`.
The command accepts a renamed task branch. It rejects symbolic links, worktrees
from another repository, and locked worktrees, including with `--force`.

Zellij must be installed. A missing session does not prevent deletion.
A session deletion failure preserves task files. If Git then fails to remove the
worktree, the session is already gone and the task files remain. Resolve the
reported error and retry. Cleanup can be retried when the worktree has already
been removed or only the named Zellij session remains.
Do not start another task session while deletion is in progress.

### `fx agent <agent> [--name <name>] [--model <model>] [-r l|m|h] [--prompt <text>] [--from <context-directory>] [--new-tab]`

Run inside a task or its worktree. The agent starts in the task directory.
The supported adapters are:

| Agent | Model | Reasoning setting |
| --- | --- | --- |
| `codex` | `gpt-6.1-sol` | `model_reasoning_effort` |
| `claude` | `claude-opus-5-5` | `--effort` |
| `glm` | `z-ai/glm-5.3` | Codex `model_reasoning_effort` |
| `deepseek` | `deepseek/deepseek-v4.1-flash` | Codex `model_reasoning_effort` |
| `gemini` | `google/gemini-3.8-flash` | Codex `model_reasoning_effort` |
| `minimax` | `minimax/minimax-m3.1-flash` | Codex `model_reasoning_effort` |

`-r l` selects low, `-r m` selects medium, and `-r h` selects high.
Omitting the flag selects medium. Other values and extra arguments are rejected.
The launcher does not substitute a different model if access fails.
Use `--model <model>` or `-m <model>` to select another model for a new session:

```bash
fx agent glm --name implement --model z-ai/glm-5.3-flash -r h
fx agent gemini --name review --model google/gemini-3.8-flash -r m
fx agent claude --name review --model claude-sonnet-5-5 -r h
```

The four OpenRouter agents use the Codex harness. They require Codex CLI and
`OPENROUTER_API_KEY` in the launching shell. Load the key from a private local
secret source. Fx does not save it in launch records or command arguments.
Provider settings apply only to the child Codex process. Fx does not modify
Claude or Codex subscription credentials, global configuration, or default providers.
The `codex` and `claude` adapters keep their existing authentication behavior.

OpenRouter's public model catalog lists these identifiers without date suffixes.
MiniMax uses the paid model. A `:free` selection is never replaced with a paid
model automatically. Each OpenRouter launch checks the exact identifier, text
output, tool support, and reasoning support against the public catalog.
Catalog failures stop launch. This check does not prove account access or full
Codex protocol compatibility. Verify a live tool-use conversation with the
selected model before relying on it for important work.
The connection uses OpenRouter's Responses API and command-backed authentication
for Codex model discovery. See the
[OpenRouter Codex guide](https://openrouter.ai/docs/cookbook/coding-agents/codex-cli).

All four adapters support unattended groups and sentry process detection through
the shared Codex implementation. Groups use each adapter's default model.
Session directories replace model slashes and colons with hyphens. The exact
selected model stays in `model.txt` and `launch.txt`. Group retries retain it.

Without `--prompt`, the agent waits for an interactive assignment. Supply it
to start work immediately in the interactive session:

```bash
fx agent codex --name review-login -r h --prompt 'Review the current changes. Write findings without editing source.'
fx agent claude --name investigate-login --prompt 'Investigate the failing login test.'
```

Use `--new-tab` from inside Zellij to open the agent in a new tab:

```bash
fx agent claude --new-tab --name investigate
fx agent codex --new-tab --name review
fx agent codex --new-tab --name review -r h --prompt 'Review the current changes without editing source.'
```

Every new session requires a name. Supply it with `--name`, or enter it at the
terminal prompt when the option is omitted. Invalid prompt input asks again.
End the input to cancel without creating a session. Commands without terminal
input must supply `--name`; they fail without creating context if it is missing.
An explicitly empty or invalid `--name` fails without prompting.

To return to a Claude conversation after exiting or pressing Ctrl+C, use the
session directory printed by its original launch:

```bash
fx agent claude --resume context/000001-investigate-claude-opus-5-5
```

Replace the example path with the actual session directory. Paths resolve from
the invoking directory and must stay inside this task's `context/`. Absolute
paths work from the task's source directory. `--new-tab` also works in Zellij.
Resume supports Claude sessions, including group members, comparisons, and task
analyses. Other providers need an executable `agents/<agent>.resume` handler.

Resume reuses the original model, reasoning, instructions, settings, findings,
starting context, and response directory. It does not send the original prompt
again. Do not combine `--resume` with `--name`, `--prompt`, `-r`, or `--from`.
The command starts from the task directory. It restores all configured fx hooks.
New callbacks append to `events/callbacks.jsonl`. Each resumed launch writes a
new `events/claude-debug-resume-<unique-id>.log` and its provider version file.
The original native log and version file remain unchanged. New final responses
continue the existing numbered `results/turn-*` directories.

The conversation identifier comes from recorded Claude hook events or captured
response metadata. A recorded startup event permits resume before any response
was captured. Missing or conflicting identifiers stop resume. Fx does not guess
the most recent conversation. The provider's own conversation history must still
exist locally. Fx logs cannot replace deleted Claude history. A partial callback
record also stops resume because further callbacks cannot append safely.
Claude sessions launched through fx hold a session lock until the process exits.
A second launch of the same session fails. Sessions opened before this support
was installed do not hold that lock; exit them before using fx resume.

Names start with a letter or digit. Remaining characters can be letters,
digits, underscores, or hyphens. Spaces are not accepted. Repeated `--name`
flags are rejected. These rules also apply to groups and comparison sessions.

Session directories use `context/<number>-<name>-<model>/`, such as
`context/000001-investigate-gpt-6.1-sol/`. Numbers increase per task across
individual launches, groups, and comparisons. Six-digit padding keeps names
in launch order when sorted. Allocation uses a locked task counter, so
concurrent launches receive different numbers. Failed launches can leave gaps.
Existing directories keep their names and remain available for handoffs.
Use the printed path to select a session with `--from`.

The tab opens in the task directory and receives focus. Its title is the
numbered session directory name, including the model. The same `--name`
option applies in the current terminal.
The tab belongs to the current Zellij session. Each invocation creates one
agent context directory. The command returns after Zellij creates the tab;
agent startup errors appear in that tab. A failed tab request preserves the
prepared context for inspection. Zellij and a current session are required.
Without `--new-tab`, the agent runs in the current terminal.

The launcher saves the exact initial text in the session's `initial_prompt.md`
and passes it as a user prompt. It does not add it to the system instructions.
Quote the text as one shell argument. Single quotes keep shell substitutions
literal. Empty assignments and repeated `--prompt` flags are rejected.
`--prompt`, `-r`, `--new-tab`, `--name`, and `--from` can appear in any order after the agent name.
The agent remains interactive when an initial prompt is supplied.

Install and authenticate each agent CLI separately. Claude Opus 5.5 requires
Claude Code 2.1.280 or later. The Claude adapter removes the inherited
`CLAUDE_CODE_EFFORT_LEVEL` variable for its child process so it cannot override
the requested effort. It does not change the parent shell environment.

Codex receives session instructions through its `developer_instructions`
configuration setting. This overrides that setting for this session only.
Claude receives an appended system prompt file. A user prompt is passed only
when `--prompt` is supplied.
Both preserve their normal permission checks. Claude adds session-specific
capture hooks through `--settings`. Codex adds diagnostic lifecycle hooks
through session configuration and uses its `notify` configuration slot
for capture during an `fx` session, replacing any custom external notifier for
that invocation. The built-in terminal notification settings still apply.
Neither adapter edits global agent configuration.
Codex runs with `--no-daemon` so diagnostic hooks inherit the current session's
output directory. Its hook commands retain the normal trust checks. Use
`/hooks` to review and trust them before relying on lifecycle event coverage.

### `fx agent group [--name <name>] [--agent <agent[:l|m|h]> ...] [--synthesis-agent <agent>] [--interactive] [-r l|m|h] [--prompt <text>] [--from <context-directory>]`

Run inside a task in a Zellij session. By default, the command opens one tab for
the group. Members run concurrently without interactive input. The tab shows their status.
Agent tabs use an explicit layout so a session template cannot replace the requested command.
This applies to groups, individual launches, comparisons, resumes, and task analyses.
After every member exits successfully with a saved final response, the runner
starts one interactive synthesis session in that same tab. You can discuss the
merged report in that session. No `--new-tab` flag is needed. By default, the
group contains five independent sessions:

| Agent | Reasoning |
| --- | --- |
| Claude | Medium |
| Codex | High |
| DeepSeek | High |
| GLM | High |
| MiniMax | Medium |

This default supports model evaluation and difficult investigations.
DeepSeek, GLM, and MiniMax require `OPENROUTER_API_KEY`.
Synthesis uses interactive Claude by default.

```bash
fx agent group --name review --prompt 'Review the current changes and record findings.'
```

Use `--interactive` to debug members in separate Zellij tabs. Each member uses
its normal interactive adapter and accepts terminal input. A group status tab
monitors their completion. Synthesis starts only when you run the compare command.
You can compare after every member saves a response, while their sessions stay open.
The comparison uses a snapshot of the responses saved when you run the command.

```bash
fx agent group --interactive --name review --agent claude:h --agent codex:h \
  --prompt 'Review the current changes and record findings.'

# Use the full group name printed at launch.
fx agent group compare 000001-review --name synthesis --new-tab
```

Interactive mode is saved in `run.json`. `fx agent group retry <group_name>`
preserves this mode and requires a Zellij session. Failed tab requests, failed
member exits, and missing responses prevent comparison. Ctrl+C in the group
status tab stops its active members. Usage summaries are available after members
exit. The group prints a compare command that includes the selected synthesis
agent. Member terminal output stays in its tab; `runner.log` records the tab request. Provider events and captured responses
remain in each member's session directory. `terminal-state.json` records the
member terminal process and exit code.

Repeat `--agent` to choose the members. These flags replace the default list.
The same agent can appear more than once. Append `:l`, `:m`, or `:h` to select
its reasoning level. Members without a level use `-r`, which defaults to medium.
The order of the options does not affect this rule.
The default Codex, DeepSeek, and GLM entries explicitly select high reasoning.
With the default list, `-r` changes only Claude and MiniMax.
Use explicit `--agent` entries to change all member levels or select fewer members.

```bash
fx agent group --name plan \
  --agent claude:h --agent codex:h --agent codex:m \
  --prompt 'Investigate the login failure and propose a repair plan.'

fx agent group --name review -r h --prompt 'Review the current changes.'
```

Every member receives the exact same prompt. The group and each member save
that text in `initial_prompt.md`. Without `--prompt`, the command requests
one assignment at the terminal before launch. A name and assignment are required
when terminal input is unavailable. Default members are listed in the tool's
`default-group` file. Adapter selection and model defaults work as for individual launches.

Each invocation requires a group name. Supply `--name` or enter the name at
the terminal prompt. Without terminal input, a missing name produces an error.
Each invocation creates a fresh numbered directory under `context/groups/`.
Groups share the task counter with individual sessions and comparisons.
Member names include their position, adapter, and model. For example:

```text
context/groups/000001-review/
├── group.md
├── initial_prompt.md
├── run.json
├── run-state.json
├── tab-request.txt
├── 1-claude-claude-opus-5-5/
│   ├── findings.md
│   ├── instructions.md
│   ├── initial_prompt.md
│   ├── launch.txt
│   ├── runner.log
│   └── events/
└── 2-codex-gpt-6.1-sol/
    └── ...
```

`group.md` lists the active members and reasoning levels. The group status tab
uses the numbered group name, such as `000001-review`. Interactive member tab
names include the group name and member directory. `run.json` records the active
member directories, synthesis provider, and interactive mode. `run-state.json`
records member status, process identifiers, exit codes, and failures. Each member keeps its own
`runner.log`, provider events, and captured responses.

After members stop, fx prints a usage table before interactive synthesis starts.
It saves the table as `usage-summary.md` and the structured data as
`usage-summary.json` in the group directory. Each attempted member also gets
`usage.json`. The records include agent, model, reasoning, outcome, elapsed
runtime, input tokens, cached input, cache writes, output tokens, reasoning
output when available, and cost in US dollars.

Input totals include cached input and cache writes. Output totals include
reasoning when the provider reports it. Subset columns must not be added to
those totals. Missing measurements are `unavailable`, not zero. Partial records
cover only reported work and can undercount failed or interrupted requests.
Claude uses `modelUsage` totals when available to include subagents; otherwise
its token counts cover only the main agent and are marked partial.

Costs are labeled `reported`, `estimated`, or `unavailable`. Claude's
`total_cost_usd` is a client estimate of API usage, not an invoice or a
subscription charge. Codex turn summaries usually provide tokens without a
dollar cost. OpenRouter agents save the selected model's catalog prices in
`pricing.json` during their existing launch check. If the CLI provides no cost,
fx estimates base token cost from that snapshot. Estimates account for reported
cache reads but exclude time discounts, tier changes, cache-write surcharges,
tool fees, and account adjustments. Missing rates or required counts leave
cost unavailable. Fx does not infer a dollar charge from subscription usage.
See [Claude cost accounting](https://code.claude.com/docs/en/agent-sdk/cost-tracking),
[Codex JSON events](https://developers.openai.com/codex/noninteractive), and
[OpenRouter usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting).

The summary includes failed and cancelled attempts. Retries retain previous
attempts and their measurements. Per-attempt runtime measures elapsed process
time, including launch preparation and tools. Group execution time measures
parallel execution across recorded runs; it is not the sum of member runtimes.
It excludes waits between retries, usage collection, and interactive synthesis.
Comparison sessions receive a snapshot of the saved table when it fits the
24 KB summary limit. Task analysis inventories these files and compares measured
cost and runtime with verified findings. A usage-reader failure marks measurements
unavailable without changing the member's investigation outcome.

Usage readers register as executable `agents/<agent>.usage` handlers. Each
receives the session directory and prints one JSON object with nullable
`input_tokens`, `cached_input_tokens`, `cache_write_input_tokens`, `output_tokens`,
`reasoning_output_tokens`, and `cost_usd`; a `cost_kind` of `reported`, `estimated`,
or `unavailable`; `coverage` of `complete`, `partial`, or `unavailable`; and a
`notes` list. Readers own provider parsing. The group runner measures runtime
and reads this shared format without provider-specific branches. Readers run
after the member process stops, with a ten-second timeout. They do not call a
model or fetch billing data.

Provider adapters expose an executable `agents/<agent>.batch` handler. It accepts
project, task, session, reasoning, and assignment arguments. It must run without
terminal input, preserve diagnostics, save a verified main-conversation response,
and return success only after completion. The runner does not contain provider
branches. Claude uses print mode for batch runs. Codex uses exec mode.

### Agent access

Pass `--access auto` or `--access full` to an agent or group launch.
New sessions default to `auto`. Set `export FX_ACCESS=full` in the VPS shell
configuration to make full access the default there. A launch flag overrides
the environment variable. Fx does not detect the machine type.

```bash
fx agent claude --name implement --access auto --prompt 'Implement the assigned change.'
fx agent codex --name implement --access full --prompt 'Implement the assigned change.'
fx agent group --name review --access auto --agent claude --agent codex \
  --prompt 'Review the current changes independently.'
```

| Access | Claude | Codex and adapters that use Codex |
| --- | --- | --- |
| `auto` | `--permission-mode auto`: classifier review; user sandbox settings apply | `--approve-for-me`: workspace sandbox with automatic approval review |
| `full` | `--permission-mode bypassPermissions`; fx sets `sandbox.enabled` to `false` | `--dangerously-bypass-approvals-and-sandbox` |

The selected mode is saved in `access.txt` in each session and group directory.
Group retries and synthesis keep that selection, even if `FX_ACCESS` changes.
Claude resumes also preserve it. Pass `--access` to resume or group compare to
override the saved mode for that session. A resume override becomes its saved
mode. A comparison override does not change the group's mode. When resuming or
comparing old sessions without a saved mode, fx uses `FX_ACCESS`, or `auto` when
it is unset. Adapters run sessions without a saved mode in auto mode.

Auto mode uses the provider's approval review. It does not approve every action.
Account policies, provider support, and explicit permission rules still apply.
Claude can fall back to manual permissions when its auto mode is unavailable.
Unattended runs cannot answer manual prompts. Permission denials fail Claude
members. Fx never retries a denied launch with full access.
See [Claude permission modes](https://code.claude.com/docs/en/permission-modes)
and [Codex automatic review](https://learn.chatgpt.com/docs/sandboxing/auto-review).

In auto mode, fx does not force Claude's Bash sandbox off. When switching a
saved full-access session to auto, fx removes its `sandbox.enabled: false`
override and preserves the other saved settings and capture hooks. Configure
Claude's sandbox in your own settings if you want operating-system isolation
in addition to classifier review.

Access handlers register as `agents/<agent>.access`. They accept `auto` or
`full`, validate support, and return a provider-specific option. Adapters without
an access handler require `--access full` or `FX_ACCESS=full`. Fx checks support
before creating a session or group. Provider mapping stays in adapter files.
Sentry retains its read-only diagnostic tools.

Assignment and repository instructions still define the scope of work.
Full access grants the access of the current account. It does not grant root
privileges or start missing services. Restart running sessions to apply
launcher changes.

A Claude result containing permission denials fails the member run. The raw
provider response remains in `events/claude-result.json`, and the capture error
names the denied tools. Automatic synthesis waits for a successful retry.

Group instructions require independent investigation. Members can read the
task rules, project memory, project context, repository, and earlier captured
responses listed in their starting context snapshot. These can include results
from earlier groups. Members must write only within their own session
directories. They must not inspect peers in the current group or scan for
results produced after the snapshot until explicitly assigned comparison work.
These are agent instructions, not filesystem access restrictions. All members
use the live task worktree. Keep source and shared context unchanged while
they investigate; the command does not snapshot the repository or shared
project files, or acquire locks on them.

Fx records one `source.json` for the group and copies it to each member.
It contains the launch commit and a hash of tracked and nonignored untracked
file contents, names, executable modes, and symlink targets. Ignored setup
files and external symlink contents are outside that identity. Submodules,
special files, inaccessible repositories, and detected concurrent edits produce
an unavailable identity. Members must report affected coverage as unverified.
The hash records an identity; it does not preserve a source copy or prevent edits.

For code reviews, each member uses its own `review-record.md`. The comparison
uses `context/review-record.md` as the persistent task record. Independent
members receive any existing task record in their starting snapshot and must
not read later updates or current peers' private records.

The launcher returns after requesting the single group tab. Tab acceptance does
not establish successful execution. The runner waits for process exit and checks
saved responses before synthesis. It uses `default-compare-agent` (Claude by
default) with medium reasoning and the automatic session name `synthesis`.
Use `--synthesis-agent <agent>` when launching the group to select any installed
interactive adapter, including `claude`, `codex`, `glm`, and `gemini`. This selection
is saved in `run.json` and also applies after a retry. It does not change the
group members selected with `--agent`.

```bash
fx agent group --name review --synthesis-agent gemini --prompt 'Review the current changes.'
```

A failed member prevents automatic synthesis. Other members finish, and their
results remain available. Ctrl+C or termination stops active member process
groups. Completed results and failed attempts remain on disk.

### `fx agent group retry <group_name>`

Run this in the terminal where the group should continue:

```bash
fx agent group retry 000001-review
```

Retry runs only incomplete members. Each retry uses a fresh member directory and
the original assignment and starting context. Successful members are reused.
Previous attempts and their logs remain unchanged. The active member list selects
which results synthesis receives. A group lock prevents concurrent runners.
Keep source unchanged during retries; the original source identity still applies.
After success, interactive synthesis starts in this terminal. A group whose
members all succeeded must use `compare` to start synthesis again.

If the Zellij tab request fails, prepared context remains available. The same
retry command can run the prepared group without opening another tab.

### `fx agent group compare <group_name> [--name <name>] [--agent <agent>] [-r l|m|h] [--new-tab]`

Use this to start a fresh synthesis of a completed group, including recovery
after synthesis fails. The command starts a single interactive comparison agent.
It supplies the original assignment and an exact list of saved member responses.
The agent must read every listed response and its source metadata in full.
The default agent is Claude with medium reasoning. It runs in the current
terminal unless `--new-tab` is supplied.

```bash
fx agent group compare review --name summary
fx agent group compare review --name summary --agent claude -r h --new-tab
fx agent group compare 000001-review --name summary --new-tab
```

Names resolve within the current task. A short name such as `review` works
when only one matching group exists. If several runs match, the command lists
their full names and stops. It never selects a run based on recency. The
default comparison agent is configured in the tool's `default-compare-agent`
file. `--agent` overrides it for one comparison.

The comparison session requires its own name through `--name` or the terminal
prompt. Without terminal input, `--name` is required. The positional group
name selects the existing group. It does not name the new session.
Comparison tabs use the numbered comparison directory name, including the model.

The comparison assignment asks the agent to combine duplicate findings,
preserve useful unique details, check disagreements against evidence, cite
member response paths, and produce one consolidated report with unresolved
questions and next steps. It merges the analysis. It does not authorize code
changes or edits to the members' results. Later responses from a member can
correct earlier ones. Previous comparison reports are excluded from the input.

For code reviews, the assignment also requires a disposition for every material
member finding in `context/review-record.md`: unresolved, fixed, accepted risk,
or dismissed. Each disposition needs evidence. Only an original decision from
me can establish accepted risk. The comparison may update this record, but
cannot fix source. Only one assigned session may write the record at a time.
The prior task record is included as a launch snapshot, even when it came from
an earlier comparison. The group source identity accompanies the responses so
the comparison can distinguish reviewed source from subsequent corrections.

Each invocation creates its own session under the selected group:

```text
context/groups/000001-review/comparisons/000002-summary-gpt-6.1-sol/
├── source-group.txt
├── input-context.md
├── initial_prompt.md
├── findings.md
├── last_turn_results.md
└── results/turn-000001/response.md
```

The agent is instructed to write the merged report to `findings.md`. Read
`last_turn_results.md` for its latest captured final response. The normal
completion callback also preserves each response in `results/`.
Later sessions can discover captured comparison reports in the task's result
index or receive one explicitly with `--from` and its comparison session path.
Repeated comparisons preserve earlier comparison sessions.

For unattended groups, the command requires successful recorded completion and
captured results from every active member. For interactive groups, every member
needs a captured response, but its session can stay open. It rejects capture errors. Legacy groups
retain their captured-response and tab-request checks; their interactive process
completion still requires manual verification.

Input paths are fixed at comparison launch. Reports remain in their captured
files instead of being copied into the initial prompt. The 48 KB context limit
applies to the assignment, response list, and prior review record. It does not
limit the combined report text. No report is silently truncated.


### Response origin and compact handoffs

Interactive Codex answers are captured through the main-conversation `Stop` hook.
Unattended Codex runs capture the final agent message from a completed exec turn.
Unattended Claude runs validate the successful print result before completion. Notifications are diagnostic events and never
publish answers. Claude capture excludes subagent stop events. Captured response
metadata identifies the provider, conversation, turn, assistant role, capture
source, and source-content identity at capture. Main-conversation origin does
not establish correctness or user approval.

Codex lifecycle hooks must be enabled and trusted in Codex. Fx does not bypass
hook trust. If the main stop hook does not run in an interactive session, no answer is captured. Legacy
responses without origin metadata remain on disk but are excluded from normal
indexes. Explicit handoff of such responses fails with a request to recapture
a main-conversation turn. Sentry separates verified main responses from raw
diagnostic output and treats missing origin as unknown.

Every new session starts with `handoff.md`. The assigned agent keeps this file
under 8,000 bytes and replaces obsolete information. It records scope, success
criteria, original approval references and limits, exact source, required test
setup, completed checks, and unresolved findings. Unknown information stays
explicitly unverified. Fx copies this summary into each captured turn.
Selecting an older turn with `--from` uses that turn's saved summary.

The existing `--from` option supplies saved responses, summaries, and recorded
source identities. The default context supplies an index plus the current task
review record, rather than all session summaries. The task review record has a
24,000-byte limit; link detailed evidence instead of copying it. The combined
handoff retains the 48 KB limit and fails instead of silently truncating.
Summaries are agent-maintained evidence. They cannot grant approval.

Normal source searches belong in `repo/`. Exclude `events/`, `.fx-sentry/`, and
`context/analyses/` from normal task searches. Diagnostic events remain outside
normal response handoffs. Read explicitly selected analysis reports separately
when assigned. Fx instructions define these search boundaries; they are not
filesystem restrictions.


## Generate and edit images

Use the Nano backend from any directory:

```bash
fx image nano --prompt 'Create a login page illustration' --output assets/login.png
fx image nano --input assets/login.png --prompt 'Use a pale blue background' --output assets/login-blue.png
```

Nano defaults to `google/gemini-nano-banana-2.1`. Use `--model` or `-m` to select
another OpenRouter image model. Repeat `--input` to supply reference images.
Inputs must be PNG, JPEG, or WebP files. The command requires
`OPENROUTER_API_KEY`. It checks the exact model's image output capability before
sending a generation request to OpenRouter's Chat Completions API with
`modalities: ["image", "text"]`. No coding harness is involved.

The command creates missing output directories. It saves one generated image
and prints its absolute path. The output extension must match the returned image
format; `.png` is the usual choice. Existing outputs are never overwritten.
The command writes through a temporary file so failures do not leave partial
output. It reports the selected model, generation identifier, and returned usage
on standard error. It does not print the key or encoded image data.

Catalog requests have a 30-second timeout. Image generation has a 300-second
timeout. Failed requests are not retried automatically because a generation
can incur charges even if its response is lost. See the
[Nano Banana API example](https://openrouter.ai/google/gemini-nano-banana-2.1/api).
Image backends register as executables in `image-adapters/`. Top-level extension
commands register in `commands/`; the core dispatch does not name image backends.

## Task sentry

Run sentry from a task directory or its `repo/` worktree:

```bash
fx agent sentry
fx agent sentry --headless
fx agent sentry --headless --interval 30
fx agent sentry --headless --once
```

Both modes use Claude Code with the `haiku` model alias. Claude Code must be
installed and authenticated. The interactive session starts with a diagnostic
assessment. Ask follow-up questions such as “Which sessions need attention?”
or “Has the implementation moved outside the task goal?” It reads fresh evidence
for the sessions that were running at launch. Start a new check to refresh process
presence. It does not check automatically between prompts.
Use `--prompt 'Check the repeated test failures'` to supply a specific focus.

Headless mode starts a fresh Claude check every 60 seconds by default.
`--interval` changes the time between check starts. A longer check delays the
next start; checks never overlap. Each check has a 90-second timeout, at most
12 agent turns, and a requested Claude budget limit of $0.25. `--timeout`
changes the timeout. The budget is a per-check limit, not a total spending
limit or a guarantee of subscription billing. `--once` runs one check and exits.
Press Ctrl+C to stop monitoring and terminate its current headless check.
A timeout, failed Claude call, exhausted limit, or empty report stops the
monitor with a nonzero exit status. It does not silently retry.

Each headless check prints a timestamped summary and one plain-text line per
session. `OK` means no ongoing progress problem was observed. `ISSUE` means
evidence shows blocked progress, repeated unsuccessful recovery, or work outside
the assignment. Only a concern gets a short reason, limited to 160 characters.
`UNKNOWN` means there is too little evidence to assess progress; it does not
count as a confirmed issue. Recovered errors, pending tests, unfinished work,
and missing `task.md` do not establish an issue on their own.

```text
[10:00:00 UTC] 1 issue
OK     implement-login
ISSUE  review-login: Repeated memory failures prevent test verification.
```

Claude returns structured classifications. The wrapper validates that every
inventoried session appears exactly once and renders the terminal text itself.
If no matching agent process is running, it prints “No running agent sessions”
without calling Claude. Use the
interactive sentry to investigate a concern in detail. This command does not
send desktop notifications or stop the monitored sessions. Automatic detection
is periodic and model-based.

Sentry explicitly receives diagnostic analysis authority for this task.
It discovers session records through `context/**/launch.txt`, including group
members and comparisons. It includes only sessions with a matching live provider
process. It reads bounded
excerpts of assignments, findings, captured responses, and files directly under
each session's `events/` directory. Reports identify truncation and missing
evidence. The read-only Claude tools can inspect additional files when needed.
Use `task.md` to state the overall goal. Without it, sentry reports uncertainty
and uses individual assignments as evidence.

Each headless check refreshes the operating system process list before reading
session logs. Provider detectors match the executable name and session-specific
launch arguments. Claude uses its settings-file argument; Codex uses its final
response callback configuration. Existing fx sessions work without relaunching
their agents. Historical directories, unrelated processes that mention a session
path, and terminated processes awaiting collection are excluded. A process that
is still open but waiting for input remains included. A matching process does
not establish useful progress. Processes can exit after the check starts.

Process inspection failures stop monitoring with a visible error. They do not
cause sentry to analyze all historical sessions. A provider registers its detector
as an executable `agents/<agent>.process` companion. Given the session directory,
it prints two lines: the native executable name and a distinctive sequence from
that session's launch arguments. Claude and Codex have detectors. Unsupported
providers produce an explicit error. Sessions outside fx's task context are not
automatically discovered. Missing events can still prevent a complete progress
assessment. Sentry reports unknown progress status when needed.

Claude receives only the `Read`, `Glob`, and `Grep` built-in tools. MCP servers,
slash commands, and configurable hooks are disabled for the sentry session.
It cannot run shell commands, edit source, or dispatch agents through its tools.
The wrapper saves its instructions, fresh `snapshot.json`, and latest headless
report in `.fx-sentry/<run-id>/` under the task. These files stay outside the
normal result index and handoffs. They contain diagnostic data; preserve them
as private task evidence. Each run gets a new directory. The latest snapshot
and report replace the previous ones within that run.

Task-specific agent commands register an executable in `agent-commands/` under
their command name. The launcher passes the project directory, task directory,
and remaining arguments to that executable. These commands own their options
and session behavior. Standard agent adapters and group launches continue to
use `agents/`.

## Captured responses and handoffs

Each agent adapter saves final response text through a CLI callback. Claude
uses the [Stop hook](https://code.claude.com/docs/en/hooks#stop).
Codex uses the [agent-turn-complete notification](https://learn.chatgpt.com/docs/config-file/config-advanced#notifications).
The capture script receives the response directly. It does not parse terminal
screens, copy tool output, or require the agent to write a file.

```text
context/000001-review-gpt-6.1-sol/
├── findings.md
├── input-context.md
├── last_turn_results.md
└── results/
    ├── turn-000001/
    │   ├── response.md
    │   └── metadata.json
    └── turn-000002/
        ├── response.md
        └── metadata.json
```

Start with `last_turn_results.md` to read a session's latest captured final
response. It contains the exact response text supplied by the CLI. The file
appears after the first successful capture. Each new captured response replaces
it atomically, so readers see a complete response. It is a current snapshot,
not an appended history. Repeated callbacks for older saved turns do not
replace it with older text. Latest means capture order within that session.

Each turn's `response.md` preserves its exact response text.
`metadata.json` identifies the agent, conversation, turn, and capture time.
Each result directory is published by an atomic rename after both files are
written. Repeated delivery of the same event does not duplicate it. Separate
turns with identical text remain separate results. The model can still write
working notes in `findings.md`; the capture script never replaces those notes.
Group members use the same structure inside their own session directories.
Do not edit the generated response files. During independent investigations,
read only the response files allowed by the starting context snapshot.
The latest-response file can change after that snapshot.

A normal new session receives an index of previously captured responses in
its starting instructions. It also saves that index in `input-context.md`.
The index makes the files discoverable; it does not force the model to read
them. To supply the actual text directly, use `--from`:

```bash
fx agent claude --name plan-login --prompt 'Plan the login fix.'

# After the planning response is captured, use its actual session directory.
fx agent codex --name implement-login --from context/000001-plan-login-claude-opus-5-5 \
  --prompt 'Implement the supplied plan.'
```

`--from` accepts a session directory, a group directory, or one specific
`results/turn-000001` directory. Repeat it to select several sources. Paths
resolve from the invoking shell's working directory and must stay inside the
current task's context. Selected responses are included in the new session's
instructions and `input-context.md`. The initial user prompt stays unchanged.

The command refuses to launch if a selected source has no captured responses,
has a recorded capture failure, or exceeds the 48 KB handoff limit. It never
silently truncates the selected responses. Select individual turn directories
for a smaller handoff. Selecting a group requires at least one captured
response from each member; this does not prove that every member has finished
all its work. Wait for the intended responses before launching the next stage.

Groups receive an index of earlier captured responses by default. The launcher
prepares this index once, before creating the group or opening any member's
tab. Every member receives the same index in its instructions and
`input-context.md`. The listed response files remain available to read.
Results captured later, including peers' responses, are not added to that
index. Group instructions limit members to the listed earlier results.
Use `--from` only to select particular earlier sources and include their full
text in every member's starting instructions.

This captures normal response-completion callbacks in newly launched `fx`
sessions. It does not retrofit existing sessions or recover earlier reviews.
Interrupted turns, process crashes, disabled hooks, managed policies, and
filesystem failures can prevent capture. Claude can also invoke Stop more
than once if another hook continues the turn; each distinct response is saved.
These callbacks are not a universal guarantee of capture under every failure.

Capture errors are reported by the callback and, when writable, saved in
`capture-error.txt`. Explicit handoffs from that session stop until the error
is investigated. A failed latest-response update can leave `last_turn_results.md`
missing or showing the previous response, while the new turn remains saved in
`results/`. Repeating the callback repairs the snapshot without duplicating the
turn. A missing completion event produces no result to hand off.
The deterministic boundary is the saved response: `--from` either supplies
the selected saved text or fails before launching. It cannot guarantee that
the model interprets or uses that text correctly.

## Diagnostic events

Every launched agent records available diagnostics in its own `events/`
directory. Group members and comparison sessions use the same layout.
Capture runs in harness callbacks and native logging code. It does not ask
the model to write event records.

```text
context/000001-review-gpt-6.1-sol/events/
├── harness-version.txt
├── callbacks.jsonl
└── codex-session.jsonl       # Codex sessions
    # or claude-debug.log    # Claude sessions
```

`callbacks.jsonl` contains one JSON object per received callback. Each record
has a schema version, agent, source, UTC receipt time, monotonic time in
nanoseconds, byte offset, and the complete parsed payload. Malformed input is
retained as raw text. Byte offsets define the saved order. Concurrent callbacks
are serialized with a file lock. Repeated deliveries remain separate records
because most lifecycle events do not have a unique delivery identifier.
Receipt times measure arrival at the capture process, not the exact time of
the underlying action. Use payload identifiers to correlate tools and turns.

The writer completes and flushes each record before returning. A failed write
attempt removes its partial record when possible. An interrupted process can
leave an incomplete last line. Further writes stop rather than mix new events
with that line. Preserve the damaged log before repairing it. Diagnostic
errors go to `events/capture-error.txt` when writable and to standard error.
They do not block final-response capture or handoffs. Check this error file
and the harness logs when assessing whether an archive is complete.

The archive contains these available sources:

- **Claude:** passive lifecycle callbacks, including tool starts and results,
  permission requests, subagent activity, turn completion and failure,
  compaction, and session start and end. The adapter also enables the native
  debug log with `--debug-file`. It does not register `WorktreeCreate` or
  `WorktreeRemove`, because these hooks replace worktree behavior. It does not
  add `FileChanged` watchers. The event names are listed in the Claude capture
  adapter and must be checked when upgrading Claude.
- **Codex:** completion notifications, configured lifecycle callbacks, and the
  native terminal session recorder. Lifecycle callbacks require trusted hooks
  and can be disabled by configuration or managed policy. The native recorder
  runs independently of hook trust. It records selected terminal events and
  outgoing operations; some events contain only their type. It is not a
  complete internal protocol trace.

Codex recording uses `CODEX_TUI_RECORD_SESSION` and
`CODEX_TUI_SESSION_LOG_PATH`. These are undocumented upstream interfaces.
This integration accepts that maintenance constraint for diagnostic use.
The installed Codex version is saved in `harness-version.txt`. Check recorder
output and hook coverage after harness upgrades. Replace this integration
when a supported equivalent provides the same recording capability.
Claude's debug log format is also owned by the harness. Neither native log
has the callback file's schema or durability guarantees. An empty reserved
native log does not prove that recording started.

This is capture of available diagnostic events, not a guarantee of every
internal event. Disabled or untrusted hooks, timeouts, crashes, and filesystem
failures can leave gaps. Synchronous callbacks also add capture overhead.
The tests cover callback storage and adapter configuration. They do not prove
complete event delivery from a live model session.

Agents must not read or search `events/` during normal work. Launch instructions
and task rules permit access only for an explicit diagnostic analysis
assignment. Event files are excluded from context indexes and comparisons.
`--from` rejects event directories and their descendants. This is an instruction
and context-selection rule, not an operating-system access restriction.
The event directory has private permissions. Raw payloads and native logs can
contain prompts, tool inputs, and tool results. No automatic retention limit
or payload truncation is applied.

The supported interfaces are described in the
[Codex hooks guide](https://learn.chatgpt.com/docs/hooks),
[Claude hooks reference](https://code.claude.com/docs/en/hooks), and
[Claude command-line reference](https://code.claude.com/docs/en/cli-reference).

## Files and context

```text
my-project/
├── .fx-project
├── project_memory.md
├── project_context/
├── repo/main/
└── tasks/fix-login/
    ├── AGENTS.md
    ├── .fx-session-sequence
    ├── repo/
    └── context/000001-review-gpt-6.1-sol/
        ├── instructions.md
        ├── findings.md
        └── launch.txt
```

`AGENTS.md` contains editable task rules. Add `task.md` if a durable task
description is useful. The `.fx-session-sequence` file stores the task counter.
Keep it when retaining task context.
The launcher creates session instructions with exact paths and a findings file.
It records the selected agent, model, and reasoning
in `launch.txt`. Session files remain available after an agent exits or fails.

Agents are instructed to read relevant context and update their own findings
after meaningful work. Final response capture is separate from these
agent-written findings. The tool cannot guarantee that a model follows the
instructions or that its findings are correct.

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
An adapter supports `check` to verify its CLI exists,
`model [model-override]` to print the selected model name without starting the CLI, and
`launch <project> <task> <session> <reasoning> [prompt]` to start it.
The launcher uses the reported model in session and tab names. Model names
contain letters, digits, underscores, dots, slashes, colons, or hyphens, with an
optional leading tilde for OpenRouter aliases. Directory names use a safe model
name. `model.txt` preserves the exact selected value for the adapter.
Use one model value for reporting, launch metadata, and the CLI argument.
The main command sets the working directory to the task before launch.
Keep model defaults and CLI-specific configuration inside the adapter.

## CLI references

- [Codex configuration](https://learn.chatgpt.com/docs/config-file/config-reference)
- [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
- [Claude CLI arguments](https://code.claude.com/docs/en/cli-reference)
- [Claude models and effort](https://code.claude.com/docs/en/model-config)
- [Zellij session commands](https://zellij.dev/documentation/commands)
- [Zellij session switching](https://zellij.dev/documentation/cli-actions#switch-session)
