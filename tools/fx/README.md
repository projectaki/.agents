# fx

`fx` prepares filesystem workspaces and starts interactive coding agents.
It uses Bash, Git, Zellij, and Python 3.9 or later. It does not schedule work. An initial assignment
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
fx agent claude --name investigate-login
```

`fx task` creates or attaches to the Zellij session `my-project-fix-login`. A new session
opens its shell in the task directory. Enter the assignment in the agent's
interactive prompt. Open another terminal
or Zellij pane, enter the same task directory, and start another session:

```bash
cd ~/work/my-project/tasks/fix-login
fx agent codex --name review-login -r h
```

Each launch requires a session name and creates a new session directory.
Omit `--name` to enter the name at an interactive terminal prompt.
It does not resume a previous conversation. Exit the agent to return to the task shell.

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

Run inside the project or one of its tasks. New tasks create a worktree on
`feature/<task_name>`. Before creating that branch, the command fetches the base
remote and starts from the updated upstream commit. The default base is recorded
by `origin/HEAD`, usually `origin/main`. The branch currently checked out in the
main clone does not affect this default.

Use `--base` to select a different starting branch:

```bash
fx task fix-login --base develop
fx task fix-login --base origin/release --no-attach
```

New task branches track the selected base as their upstream. An upstream is
the branch Git uses by default for pull and for ahead/behind comparisons.
For a remote base such as `origin/develop`, the task tracks that remote branch.
An explicit name resolves to a local branch first, then a remote-tracking branch.
For a local base, the task starts from and tracks its configured upstream if
present, otherwise `origin/<base-name>` if available. Thus `--base main` starts
from the fetched `origin/main` when local `main` tracks it. Unpushed commits on
local `main` are not included. The main clone's branch and files are preserved.
If neither upstream exists, the task starts from and tracks the local base.
The command reports this local-only base because it has no remote updates.
Tags and commit identifiers are not accepted as branch names.

The command fetches the configured upstream remote, or `origin` when none is
configured. An explicit remote prefix such as `upstream/develop` selects that
remote. Fetching updates its configured remote-tracking references and prunes
references to deleted remote branches. A failed fetch stops creation without
creating a task branch or worktree. It does not use cached commits as a fallback.
An upstream deleted from the remote produces an error. A base that tracks a
local branch uses that branch without a network fetch.

Multiple tasks can use the same base branch, even while that branch is checked
out in the main clone. Each task checks out its own `feature/<task_name>` branch.
For example, tasks `first` and `second` with `--base main` use `feature/first`
and `feature/second`. Each starts at the latest fetched base commit when it is
created. Their later commits are independent.
Reopening the same task reuses its worktree. The tool does not force one task
branch into multiple worktrees.

If the recorded default reference is missing, the command attempts to discover it
from `origin`. If discovery fails, supply `--base`. The directory named
`repo/main` can use any default branch name.

An existing task branch can be attached if it is not checked out elsewhere.
A conflicting checkout or worktree produces an error. Existing task files and
customized instructions are preserved. A switched task branch is not reset.
Reopening an existing task or attaching an existing task branch does not fetch.
For these tasks, `--base` updates only the upstream using available references.
It does not reset commits, merge, rebase, or replace uncommitted files.
Omitting `--base` preserves the existing upstream. An invalid base produces an error.

Run these commands inside the task's `repo/` directory to retrieve base updates
and then merge them into the task branch:

```bash
git fetch
git merge '@{upstream}'
```

`git fetch` updates the remote references without changing the task's files.
Use `git rebase '@{upstream}'` instead of the merge command if you want to
replay task commits on the updated base.

To publish the task branch while retaining the base as its upstream, use
`git push origin HEAD`. Using `git push -u` would instead set the published
task branch as the upstream.

Existing tasks on `<task_name>` or `codex/<task_name>` remain supported and keep
their names. When attaching an existing branch, the command checks
`feature/<task_name>` first, then `<task_name>`, then `codex/<task_name>`.
To configure their upstream, run `fx task <task_name> --base origin/main --no-attach`.
To use the feature prefix for an existing branch, run `git branch -m feature/<task_name>`
inside its `repo/` directory. Git rejects the rename if that branch name
already exists. All supported names remain compatible with `fx agent`.

Task creation copies Git-ignored `appsettings.json` and `appsettings.*.json`
files from the project's `repo/main` clone into the task worktree. It preserves
their relative paths and file permissions, including files in nested directories.
Put the local development settings in that clone before creating a task.
Git cloning does not retrieve ignored settings from another checkout.

Reopening a task copies missing settings as well. It never overwrites an
existing task file or link. To fill missing settings without attaching to Zellij:

```bash
fx task fix-login --no-attach
```

A file must be ignored in both the main clone and the task worktree.
Tracked files, including tracked files deleted in the task, are not copied.
Other ignored files, such as `.env`, are not copied. Source symbolic links
are skipped. A symbolic link in a missing file's destination directory path
causes an error. Copy failures preserve the worktree and existing settings;
rerun the task command after correcting the problem. Settings are independent
copies, so later changes in the main clone do not update existing task files.

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

### `fx agent <agent> [--name <name>] [-r l|m|h] [--prompt <text>] [--from <context-directory>] [--new-tab]`

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
fx agent codex --name review-login -r h --prompt 'Review the current changes. Write findings without editing source.'
fx agent claude --name investigate-login --prompt 'Investigate the failing login test.'
```

Use `--new-tab` from inside Zellij to open the agent in a new tab:

```bash
fx agent claude --new-tab --name investigate
fx agent codex --new-tab --name review
fx agent codex --new-tab --name review -r h --prompt 'Review the current changes without editing source.'
```

Every session requires a name. Supply it with `--name`, or enter it at the
terminal prompt when the option is omitted. Invalid prompt input asks again.
End the input to cancel without creating a session. Commands without terminal
input must supply `--name`; they fail without creating context if it is missing.
An explicitly empty or invalid `--name` fails without prompting.

Names start with a letter or digit. Remaining characters can be letters,
digits, underscores, or hyphens. Spaces are not accepted. Repeated `--name`
flags are rejected. These rules also apply to groups and comparison sessions.

Session directories use `context/session-<name>-XXXXXXXX/`. The random suffix
keeps repeated and concurrent launches separate. Use the printed directory
path to refer to a specific session or supply it with `--from`.

The tab opens in the task directory and receives focus. Its title is the
session name. The same `--name` option applies in the current terminal.
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

### `fx agent group [--name <name>] [--agent <agent[:l|m|h]> ...] [-r l|m|h] [--prompt <text>] [--from <context-directory>]`

Run inside a task in a Zellij session. The command opens one interactive tab
per member. The agents run concurrently after their tabs open. No `--new-tab`
flag is needed. By default, the group contains one Claude session and one Codex
session, both with medium reasoning:

```bash
fx agent group --name review --prompt 'Review the current changes and record findings.'
```

Repeat `--agent` to choose the members. These flags replace the default list.
The same agent can appear more than once. Append `:l`, `:m`, or `:h` to select
its reasoning level. Members without a level use `-r`, which defaults to medium.
The order of the options does not affect this rule.

```bash
fx agent group --name plan \
  --agent claude:h --agent codex:h --agent codex:m \
  --prompt 'Investigate the login failure and propose a repair plan.'

fx agent group --name review -r h --prompt 'Review the current changes.'
```

Every member receives the exact same prompt. The group and each member save
that text in `initial_prompt.md`. Without `--prompt`, each session waits for
interactive input. Default members are listed in the tool's `default-group`
file. Adapter selection and model defaults work as for individual launches.

Each invocation requires a group name. Supply `--name` or enter the name at
the terminal prompt. Without terminal input, a missing name produces an error.
Each invocation creates a fresh directory under `context/groups/`. A random
suffix distinguishes repeated runs and concurrent launches. For example:

```text
context/groups/review-Ab12Cd34/
├── group.md
├── initial_prompt.md
├── 1-claude/
│   ├── findings.md
│   ├── instructions.md
│   ├── initial_prompt.md
│   ├── launch.txt
│   └── tab-request.txt
└── 2-codex/
    └── ...
```

`group.md` lists the members, reasoning levels, and tab titles. Tabs use the
group directory name plus the member number and agent name, such as
`review-Ab12Cd34-1-claude`. They are individual tabs in the current Zellij
session. The shared prefix identifies the group.
Member session names use the member number and agent name within the named
group. The command does not prompt separately for each member.

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

After every member finishes, start a separate agent to compare the results.
Use the short group name if it identifies one run, or the full name printed
by the launcher:

```bash
fx agent group compare review --name summary --new-tab
```

The group command returns after requesting the tabs. It does not wait for
agent completion or merge results automatically. It validates all selected
agent commands before creating context. Authentication and model errors can
still occur when the agent starts and appear in its tab.

Each member's `tab-request.txt` records `pending`, `requesting`, `accepted`,
or `failed: <exit code>`. These describe the tab request, not agent progress.
If a request fails, the command stops and returns its exit code. It preserves
all prepared context and leaves earlier tabs running. Inspect those tabs and
the request files before retrying. Running the command again creates a new
group; it does not retry members within the existing group.

### `fx agent group compare <group_name> [--name <name>] [--agent <agent>] [-r l|m|h] [--new-tab]`

Run this after every group member has finished its intended responses. The
command starts a single interactive comparison agent. It supplies the group's
original assignment, when present, and the captured responses from every
member. The default agent is Codex with medium reasoning. It runs in the
current terminal unless `--new-tab` is supplied.

```bash
fx agent group compare review --name summary
fx agent group compare review --name summary --agent claude -r h --new-tab
fx agent group compare review-Ab12Cd34 --name summary --new-tab
```

Names resolve within the current task. A short name such as `review` works
when only one matching group exists. If several runs match, the command lists
their full names and stops. It never selects a run based on recency. The
default comparison agent is configured in the tool's `default-compare-agent`
file. `--agent` overrides it for one comparison.

The comparison session requires its own name through `--name` or the terminal
prompt. Without terminal input, `--name` is required. The positional group
name selects the existing group. It does not name the new session.
Comparison tabs use the full group directory name followed by the session name.

The comparison assignment asks the agent to combine duplicate findings,
preserve useful unique details, check disagreements against evidence, cite
member response paths, and produce one consolidated report with unresolved
questions and next steps. It merges the analysis. It does not authorize code
changes or edits to the members' results. Later responses from a member can
correct earlier ones. Previous comparison reports are excluded from the input.

Each invocation creates its own session under the selected group:

```text
context/groups/review-Ab12Cd34/comparisons/session-summary-XXXXXXXX/
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

The command requires at least one captured response from every member and
rejects recorded capture errors or tab requests that were not accepted.
These checks establish that results are available. They do not establish that
an interactive agent has stopped working or will produce no more responses.
The command does not wait for completion; run it after checking the member
sessions. Input is fixed at comparison launch. The same 48 KB handoff limit
applies. If the combined input is larger, use a normal agent launch with
`--from` selecting the relevant individual turns.

## Captured responses and handoffs

Each agent adapter saves final response text through a CLI callback. Claude
uses the [Stop hook](https://code.claude.com/docs/en/hooks#stop).
Codex uses the [agent-turn-complete notification](https://learn.chatgpt.com/docs/config-file/config-advanced#notifications).
The capture script receives the response directly. It does not parse terminal
screens, copy tool output, or require the agent to write a file.

```text
context/session-review-XXXXXXXX/
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
fx agent codex --name implement-login --from context/session-plan-login-XXXXXXXX \
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
context/session-review-XXXXXXXX/events/
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
    ├── repo/
    └── context/session-review-XXXXXXXX/
        ├── instructions.md
        ├── findings.md
        └── launch.txt
```

`AGENTS.md` contains editable task rules. Add `task.md` if a durable task
description is useful. The launcher creates session instructions with exact
paths and a findings file. It records the selected agent, model, and reasoning
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
