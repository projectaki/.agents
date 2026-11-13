---
name: fx-cli
description: "Set up and use the projectaki fx CLI for project clones, task worktrees, terminal sessions, coding agents, independent review groups, and saved response handoffs. Use when asked to install or configure fx, prepare an fx task, launch agents through fx, compare group results, or troubleshoot an fx workspace. Excludes the unrelated fx JSON processor and foreign exchange tools."
---

# fx CLI

Use `fx` to prepare workspaces and start interactive coding agents. The sentry
command can repeat diagnostic checks. Rex groups run independent investigations
in one tab with one interactive pane per member. Use the compare command to
start synthesis. A worktree is a separate Git checkout that shares repository
history.

## Check the environment

Run `type -a fx` and `fx --help` once. Confirm the help lists `setup`, `task`,
`agent`, and `shell-init`. Another program also uses the name `fx`.
If the command is absent, resolves to another tool, or lacks shell integration,
read [Machine setup](references/setup.md). That guide covers dependencies,
authentication, persistent shell configuration, and installation checks.

Use the installed help and its adjacent `README.md` for version differences.
In this repository, the implementation is `tools/fx/`. Keep its companion
files together. Do not install a package named `fx` from a package registry.

## Choose the execution mode

- In an interactive Bash or Zsh shell, load `shell-init`. Then `fx setup` and
  `fx task --no-attach` change the current directory.
- In a command runner, use the absolute executable path and `--no-attach`.
  Set the working directory explicitly on later calls. Shell state does not
  necessarily persist between tool calls.
- A normal `fx task` prefers Rex on the machine that holds the worktree. For
  new sessions it falls back to Zellij. Set `FX_MULTIPLEXER=rex` or
  `FX_MULTIPLEXER=zellij` to require a backend for a new session.
  Do not capture that command's output with command substitution.
- Agent sessions remain interactive even with `--prompt`. Use an interactive
  terminal, or `--new-tab` from inside an existing Rex or Zellij session. Do not treat
  standard agent launches as an unattended batch interface. Group members use
  explicit batch adapters. Sentry's explicit
  `--headless` mode supports unattended diagnostic checks.

## Prepare a project and task

Reuse the intended project and task when they exist. Run setup and task
creation sequentially. Substitute actual paths and names in these examples.

Open a local shell or select the virtual private server (VPS) in Rex and open
a shell there. Use SSH and Zellij if Rex is unavailable on the VPS.
In an interactive shell with integration loaded:

```bash
fx setup my-project owner/repository
fx task fix-login
```

Command runner without shell integration:

```bash
fx_bin="$HOME/.agents/tools/fx/fx"
project_dir="$("$fx_bin" setup my-project owner/repository)" || exit
cd -- "$project_dir" || exit
task_dir="$("$fx_bin" task fix-login --no-attach)" || exit
cd -- "$task_dir/repo" || exit
git status --short --branch
```

Set `FX_ROOT` before setup to change the project root from `$HOME/work`.
Repository inputs accept `owner/repository`, a Git URL, or a local path.
Only the shorthand requires authenticated `gh`, the GitHub command-line tool.
Without a repository, setup creates directories and memory only. Tasks require
a clone with at least one commit.

The project contains `repo/main/`, `project_memory.md`, and `project_context/`.
Each task contains `repo/`, `AGENTS.md`, and `context/`. Agents start in the
task directory. Source commands run in its `repo/` directory. Read task and
repository instructions before edits.

New terminal sessions show the directory, repository path, latest
commit, and Git status in their initial terminal, then start the task
orchestrator. Set `FX_ORCHESTRATOR_AGENT` to `claude` or `codex`, or choose at
the terminal prompt. Exiting opens the interactive `SHELL` (Bash when unset).
Run `fx orchestrator` from the task or its worktree to start a fresh session in
the current terminal. It receives paths to the task instructions and CLI
reference. It launches assigned agents in new terminal tabs. Fx skips context and
event capture for the orchestrator. Existing sessions keep their backend and terminals.
`--no-attach` keeps standard output limited to the task path.

Without `--base` or `--onto`, existing task worktrees keep their branch and files.
When no worktree exists, fx reuses an existing `feature/<task-name>`, `<task-name>`,
or `codex/<task-name>` branch. If none exists, fx creates `feature/<task-name>`
from the fetched default branch. Reopening does not fetch or reset.

Use `--base feature/export` without `--onto` to check out that branch in the task worktree.
An existing local branch keeps its commits and upstream, without fetching.
If no local branch matches, fx fetches `origin` and looks for the remote branch.
Use `--base upstream/feature/export` to select another remote explicitly.
A remote-only branch creates local `feature/export` tracking that remote branch.
An existing local counterpart keeps its current commits and upstream.
A missing local name creates that branch from the fetched default, without an
upstream or a push. Missing remote-prefixed names fail. Tags and commit identifiers
are not accepted.

Use `fx task export-validation --base feature/export-validation --onto feature/export`
to create a new branch at the tip of `feature/export`. Omit `--base` to use
`feature/<task-name>` for the new branch. Fx fetches `origin` to check that the
new branch name is available. The start branch uses the local tip when
available and otherwise uses the fetched branch on `origin`. Use
`--onto origin/feature/export` to select the fetched tip explicitly. The new
branch has no upstream. Set the pull request base to `feature/export` when you
open it. Omit `--onto` to reopen the task. Fx rejects `--onto` for an existing
worktree or destination branch.

An explicit `--base` takes priority over old task branches. Reopening with a
different branch switches the worktree, preserving the old branch and commits.
Switching requires no uncommitted or untracked files. Git rejects switches that
would overwrite ignored files. Reopening on the same branch preserves local work.
If the selected branch is already checked out in another worktree, fx fails.
Do not force duplicate branch checkouts. All branch names work with `fx agent`.

Existing Git-ignored files are copied from the main clone. Existing untracked
files selected by the root `.worktreeinclude` file are copied too. This file
uses Git ignore pattern syntax to select additional files. All ignored files
are eligible, including dependencies and build output. Existing task files and
files tracked in the task are preserved. Source symbolic links are skipped.
Reopening fills missing eligible files. Copies preserve relative paths and
permissions. Put needed local files in the main clone before creating a task.

## Analyze a task's recorded history

Use `fx task analyze <task_name>` from the project directory for an assigned
retrospective. Inside a task or its worktree, omit the task name. This starts an
interactive agent with an explicit assignment to inspect all recorded provider
events, closed sessions, review groups, and comparisons for this task.

```bash
fx task analyze fix-login
fx task analyze --agent claude -r h --new-tab
```

The default provider comes from `default-analyze-agent` (`codex` by default).
Reasoning defaults to high. `--new-tab` requires an existing Rex or Zellij session.
This command supplies its own assignment and session name. It does not create
or reopen the selected task. `analyze` is a reserved task action name.

Each run writes `evidence-inventory.json` and its own `findings.md` under
`context/analyses/<number>-analyze-<model>/`. Normal response capture preserves
the final report. The assignment requires full log coverage in bounded chunks,
detailed sequences, exact citations, and explicit unread ranges. It traces
later defects through planning, implementation, reviews, discovery, and proof.
It covers memory failures, crashes, retries, recovery, and instruction conflicts.
Recommendations must identify a specific project instruction, skill, or helper
to change and how to validate the change. The assignment permits writing only
its own report and notes.
Normal provider permissions still apply; this is not a filesystem sandbox.
Analysis includes group usage summaries, per-attempt measurements, and saved
price snapshots. Compare measured cost and runtime with verified useful findings.
Include failed attempts and retries. Keep estimated costs separate from billing.

The inventory excludes prior analyses, symbolic links, and the source worktree.
The analyst reads relevant source and instructions separately. Files can change
after inventory. Missing logs and historical instruction versions limit claims.
Do not claim full coverage from inventory alone. Keep recommendations as proposals
until assigned implementation. Reports can support later comparisons; the
command does not aggregate findings across tasks automatically.

## Launch an assigned agent

Launching an agent requires an assignment within the user's authorized scope.
Always supply `--name` and a complete `--prompt` when starting a new session in
automated invocations. Resume uses the original session and its conversation.
Names start with a letter or digit and contain only letters, digits,
underscores, or hyphens. This rule also applies to projects, tasks, and groups.

```bash
fx agent codex --name review-login -r h --new-tab \
  --prompt 'Review the login changes. Do not edit source. Report findings with file paths and evidence.'
```

Omit `--new-tab` to use the current interactive terminal. The option requires
an existing Rex or Zellij session. Each new launch creates a new conversation and a numbered context directory
ending in the model name, even when the name is reused. Numbers increase per
task across sessions, groups, and comparisons. Record the printed context path.

Adapters are executable files in `tools/fx/agents/`. Model selection belongs
to those adapters. Inspect the selected adapter when exact model choice matters;
do not invent a model flag or substitute a model after an access error.
Reasoning levels are `l` (low), `m` (medium, the default), and `h` (high).
Access defaults to `auto`. Pass `--access auto` for provider approval review or
`--access full` to bypass approvals and sandboxing. Set `export FX_ACCESS=full`
in the VPS shell configuration to select full access there. An explicit flag
overrides that default. Fx does not detect the machine type. Native provider
support and managed policies still apply; auto does not approve every action.
The selected mode is saved in `access.txt`. New tabs, group retries, synthesis,
and resumes preserve it. Resume and group compare accept `--access` to
override the saved selection. Resuming or comparing old sessions without a
selection uses the machine default. Custom adapters need an
`agents/<agent>.access` handler for auto mode.
Keep prompt text in one safely quoted argument. For complex text, read it from
a file with `--prompt "$(cat /absolute/path/assignment.txt)"`.

Only one session may edit task source at a time. Shared project memory and
context also need one assigned editor. Other sessions can investigate without
edits. A returned tab request confirms tab creation, not successful agent work.

## Resume a conversation

Use the original session directory printed at launch:

```bash
fx agent claude --resume context/000001-review-claude-opus-5-5
fx agent codex --resume context/000002-review-gpt-6.1-sol --new-tab
fx agent deepseek --resume context/000003-review-deepseek-deepseek-v4.1-flash --new-tab
```

Resume supports Claude, Codex, DeepSeek, Gemini, GLM, and MiniMax.
Use the actual path inside the current task's context. Relative paths start
in the invoking directory. Absolute paths also work. `--new-tab` works in
Rex and Zellij. Group members, comparisons, and analyses can be resumed by
their own session directories. Other adapters need an executable
`agents/<agent>.resume` handler.

Resume uses the saved provider, model, reasoning, instructions, and access mode. Use
`--access` to override access. The starting context, findings, and captured
responses stay in the same session. The conversation continues from local
provider history without sending the original prompt again. Use
`--name`, `--model`, `--prompt`, `-r`, and `--from` for new sessions.

Fx requires exactly one conversation identifier from recorded hooks or
saved response metadata. The startup hook can supply it before the first
response. Incomplete callback records stop resume. Exit the original
conversation before resuming it. Current fx launches hold a session lock.

New callbacks append to the original callback log. Each resume writes a
separate native log. Codex hooks require trust in the Codex CLI.

## Inspect task sessions with sentry

Run `fx agent sentry` inside a task or its worktree to open an interactive,
read-only Claude Haiku session. It starts with a diagnostic assessment of sessions
that have a matching live provider process. Follow-up questions use fresh file
evidence for that starting list; start a new check to refresh process presence.
This command supplies its
own assignment and does not require `--name` or `--prompt`.

```bash
fx agent sentry
fx agent sentry --headless --interval 30
fx agent sentry --headless --once
```

Headless checks start every 60 seconds by default and never overlap. Each uses
a fresh conversation, a 90-second timeout, at most 12 turns, and a requested
$0.25 Claude budget limit. `--timeout` changes the timeout. A failed or timed-out
check stops monitoring with an error. Ctrl+C stops the current headless check.
Headless output is one plain-text status per session: `OK`, `ISSUE`, or `UNKNOWN`.
Only a concern gets a short reason. Issues require evidence of blocked progress,
repeated unsuccessful recovery, or work outside the assignment. Recovered errors
and unfinished work do not count on their own. Use interactive mode for details.
Desktop notifications and process intervention are not implemented.
`--prompt` supplies an optional diagnostic focus.

Sentry has explicit authority to inspect this task's diagnostic events. Each
headless check filters `launch.txt` records to matching live provider processes,
including group members and comparisons. Closed sessions are excluded before
reading logs or calling Claude. Claude and Codex have process detectors in
`agents/<agent>.process`; other providers need their own detector. A process-list
failure stops monitoring with an error. An open agent waiting for input still
counts as running. It uses bounded log excerpts and reports missing evidence.
The overall goal comes from `task.md` when present. Its tools only read files.
Its snapshots and latest headless report live under `.fx-sentry/<run-id>/`,
outside normal captured response indexes and `--from` handoffs.

## Independent groups and comparison

Use groups for an assigned independent investigation. Run inside the task in
Rex or Zellij. Every member receives the same prompt and shares the live worktree.
Keep source and shared context unchanged until their investigations finish.

```bash
fx agent group --name review --agent claude:h --agent codex:h \
  --prompt 'Review the current changes independently. Do not edit source. Record supported findings in your own session directory.'
```

The default group runs Claude, Codex, DeepSeek, GLM, and MiniMax.
Codex, DeepSeek, and GLM explicitly use high reasoning. Claude and MiniMax
use `-r`, which defaults to medium. The three OpenRouter agents require
`OPENROUTER_API_KEY`. Repeated `--agent` flags replace `default-group`.
Members without an explicit level use `-r`. Supply `--prompt` or enter one
assignment before launch. Members must read only the earlier responses listed
in their starting context snapshot and keep their findings private from peers
in the current group.

In Rex, the command opens one tab with one interactive pane per member.
After every member saves a response, start comparison manually:

```bash
fx agent group compare 000001-review --name synthesis --new-tab
```

Use the full group name printed at launch. Members can stay open. Use `--agent`
on the compare command to select the comparison adapter. Comparison reads the
saved responses available at launch. Failed members block comparison.

In Zellij, the default group runs without interactive input in a status tab
and starts synthesis there after all members exit successfully with saved
responses. Use `--synthesis-agent` to select the synthesis adapter. Use
`--interactive` to open separate member tabs and compare manually.

Each member saves its response and diagnostic logs. After members exit, fx
saves `usage-summary.md` and `usage-summary.json`. Members save `usage.json`.
Missing values are unavailable. Provider costs may be estimates.

To retry incomplete members, use:

```bash
fx agent group retry 000001-review
```

Retries use fresh member directories and preserve successful responses and
failed attempts. The original assignment, context snapshot, and source
identity still apply. Rex retries open one tab with one pane per incomplete
member. Zellij retries preserve the original mode. Inspect `run-state.json`
and each member's `runner.log` for failures. For Rex, inspect
`group-runner.log` for group startup errors.

For unattended Zellij groups, adapters implement execution in
`agents/<agent>.batch`. The group runner uses the registered adapters.
Claude uses print mode. Codex uses exec mode.
Auto access selects Claude's `--permission-mode auto` or Codex's
`--approve-for-me`, including batch members and synthesis. Full access selects
Claude's `bypassPermissions` mode with its shell sandbox disabled, or Codex's
`--dangerously-bypass-approvals-and-sandbox`. Fx supplies no tool-specific
allowlist. Managed policies and explicit deny or ask rules can still restrict
access. Assignment and repository instructions still define the scope.
A Claude permission denial fails the member instead of publishing it as complete;
inspect the preserved provider result and capture error before retrying.
A successful exit does not prove full coverage.

Each group records one `source.json` identity and supplies it to every member.
This identifies the commit and tracked plus nonignored untracked source content.
It is not a preserved source copy. Keep the live source unchanged during review.
Report unavailable identity or changed source as a verification gap.
For code review, members use private session review records. Comparison carries
every material finding into `context/review-record.md` with its disposition and
evidence. Only one assigned session may update that task record. Only an original
decision from me can establish accepted risk. Subsequent launches receive a
snapshot of the prior task record, including earlier comparison decisions.

## Read results and pass context

- `findings.md` contains agent-written working notes.
- `last_turn_results.md` contains the latest captured final response.
- `results/turn-*/response.md` preserves individual captured responses.
- `input-context.md` records the supplied context snapshot.
- `handoff.md` is the agent-maintained current summary of scope, success criteria,
  approval references and limits, source, setup, checks, and unresolved findings.
  Keep it under 8,000 bytes. Fx saves a copy with each captured response.
- `source.json` identifies source at launch. Response metadata identifies source
  at capture. Ignored files, external symlink contents, and build identity need
  separate setup evidence. Submodules and special files produce unavailable identity.

Do not edit generated response files. During independent investigation, read
only the earlier response paths allowed by the starting snapshot.
The default index lists earlier responses; it does not include their full text.
Interactive Codex captures main-conversation `Stop` hooks. Batch capture uses
completed provider output. Notifications never publish answers.
Hooks must be enabled and trusted in Codex. Fx does not bypass trust.
Responses without origin metadata remain on disk but are excluded from the index
and cannot be supplied with `--from`. Recapture a main-conversation turn.
Verified assistant origin does not establish user approval or correct conclusions.
Normal source searches stay in `repo/`; exclude diagnostic and analysis directories.
The current task review record is supplied as a launch snapshot, up to 24,000 bytes.
Use `--from` to include selected saved text in a new session:

```bash
fx agent codex --name implement-login --new-tab \
  --from context/000001-plan-login-gpt-6.1-sol/results/turn-000001 \
  --prompt 'Implement the supplied plan and run the relevant tests.'
```

Use an actual captured directory. Paths resolve from the invoking directory
and must remain in this task's context. Repeat `--from` for multiple sources.
A source can be a session, a group, or one turn. The total limit is 48 KB.
Select individual turns when necessary. Missing responses or recorded capture
errors stop the launch. One saved turn per member does not prove group completion.

## Recover or clean up

- If setup rejects a different repository, select the correct project. Do not
  replace the clone to bypass the check.
- If base discovery or fetch fails, inspect the reported remote and branch.
  Supply an existing remote base or a local `--base` when needed.
  Do not reset work or use stale commits.
- If opening the terminal session fails after task preparation, reuse the task. It remains
  available through `--no-attach`.
- If a group tab request fails, inspect the group's launch records. For Rex,
  wait for or close any open members. Use `fx agent group retry <full-group-name>`
  to recover the group. A fresh `group` invocation creates a different group.
- If capture fails, inspect the session's `capture-error.txt` and saved turns.
  Do not claim that a missing response was captured or delete error markers
  merely to bypass a handoff failure.
- Read or search `events/` only for an explicitly assigned diagnostic analysis.
  Diagnostic events are not task context and cannot be passed with `--from`.

For requested deletion, run `fx delete <task-name>` from the project directory,
outside the target terminal session. The saved backend must be reachable. Deletion stops the
session and removes the task, context, and captured results. Git branches remain.
Inspect source status and needed context first. Use `--force` only when loss
of uncommitted, untracked, ignored, or detached work is explicitly authorized.
Never use deletion as routine recovery for a failed launch.
