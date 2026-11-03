---
name: fx-cli
description: "Set up and use the projectaki fx CLI for project clones, task worktrees, Zellij sessions, coding agents, independent review groups, and saved response handoffs. Use when asked to install or configure fx, prepare an fx task, launch agents through fx, compare group results, or troubleshoot an fx workspace. Excludes the unrelated fx JSON processor and foreign exchange tools."
---

# fx CLI

Use `fx` to prepare workspaces and start interactive coding agents. The sentry
command can repeat diagnostic checks. Other commands do not schedule work or
wait for groups to finish. A worktree is a separate Git
checkout that shares repository history.

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
- A normal `fx task` opens or attaches to Zellij, a terminal session manager.
  Do not capture that command's output with command substitution.
- Agent sessions remain interactive even with `--prompt`. Use an interactive
  terminal, or `--new-tab` from inside an existing Zellij session. Do not treat
  standard agent launches as an unattended batch interface. Sentry's explicit
  `--headless` mode supports unattended diagnostic checks.

## Prepare a project and task

Reuse the intended project and task when they exist. Run setup and task
creation sequentially. Substitute actual paths and names in these examples.

Interactive shell with integration loaded:

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

New tasks use `feature/<task-name>` and the fetched default base from
`origin/HEAD`. Use `--base develop` or `--base origin/release` when required.
A local base with an upstream uses the fetched upstream, not its unpushed
local commits. A missing local base is created from the fetched default branch.
It has no upstream and is not pushed. The task tracks that new local base.
Missing remote-prefixed bases still fail. Tags and commit identifiers are not
accepted. If task naming conflicts with project rules, resolve that before
creation; there is no branch-prefix flag.

Existing tasks preserve files and branches. Reopening does not reset. It fetches
only when an explicit local base is missing and must be created.
For existing tasks, `--base` changes the upstream only. It does not move commits.
New branches track the base. When publication is requested, `git push origin HEAD`
retains that relationship; adding `-u` changes it to the published branch.

Only ignored `appsettings.json` and `appsettings.*.json` files are copied from
the main clone. Existing task files are preserved. Files such as `.env` are
not copied. Reopening fills missing eligible settings.

## Launch an assigned agent

Launching an agent requires an assignment within the user's authorized scope.
Always supply `--name` and a complete `--prompt` in automated invocations.
Names start with a letter or digit and contain only letters, digits,
underscores, or hyphens. This rule also applies to projects, tasks, and groups.

```bash
fx agent codex --name review-login -r h --new-tab \
  --prompt 'Review the login changes. Do not edit source. Report findings with file paths and evidence.'
```

Omit `--new-tab` to use the current interactive terminal. The option requires
an existing Zellij session. Each launch creates a new conversation and a numbered context directory
ending in the model name, even when the name is reused. Numbers increase per
task across sessions, groups, and comparisons. Record the printed context path.

Adapters are executable files in `tools/fx/agents/`. Model selection belongs
to those adapters. Inspect the selected adapter when exact model choice matters;
do not invent a model flag or substitute a model after an access error.
Reasoning levels are `l` (low), `m` (medium, the default), and `h` (high).
Keep prompt text in one safely quoted argument. For complex text, read it from
a file with `--prompt "$(cat /absolute/path/assignment.txt)"`.

Only one session may edit task source at a time. Shared project memory and
context also need one assigned editor. Other sessions can investigate without
edits. A returned tab request confirms tab creation, not successful agent work.

## Inspect task sessions with sentry

Run `fx agent sentry` inside a task or its worktree to open an interactive,
read-only Claude Haiku session. It starts with a diagnostic assessment and
answers follow-up questions using fresh evidence. This command supplies its
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
Reports appear in the terminal; desktop notifications and process intervention
are not implemented. `--prompt` supplies an optional diagnostic focus.

Sentry has explicit authority to inspect this task's diagnostic events. It
includes all provider sessions with `launch.txt`, group members, and comparisons.
It uses bounded log excerpts and reports missing evidence and unknown liveness.
The overall goal comes from `task.md` when present. Its tools only read files.
Its snapshots and latest headless report live under `.fx-sentry/<run-id>/`,
outside normal captured response indexes and `--from` handoffs.

## Independent groups and comparison

Use groups for an assigned independent investigation. Run inside the task in
Zellij. Every member receives the same prompt and shares the live worktree.
Keep source and shared context unchanged until their investigations finish.

```bash
fx agent group --name review --agent claude:h --agent codex:h \
  --prompt 'Review the current changes independently. Do not edit source or shared context. Record supported findings in your own session directory.'
```

Repeated `--agent` flags replace `default-group`. Members without an explicit
level use `-r`, which defaults to medium. No `--new-tab` flag is needed.
Members must not read current peers' findings or later results. They may read
earlier responses listed in their starting context snapshot.

After every member finishes the intended response, compare the full group
name printed at launch:

```bash
fx agent group compare 000001-review --name summary --new-tab
```

Replace the example number with the actual one. Short names work only when
one group matches. Comparison uses `default-compare-agent`; `--agent` can
override it. Comparison combines analysis and checks disagreements. It does
not authorize source edits. Read its own captured response for the outcome.

## Read results and pass context

- `findings.md` contains agent-written working notes.
- `last_turn_results.md` contains the latest captured final response.
- `results/turn-*/response.md` preserves individual captured responses.
- `input-context.md` records the supplied context snapshot.

Do not edit generated response files. During independent investigation, read
only the earlier response paths allowed by the starting snapshot.
The default index lists earlier responses; it does not include their full text.
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
- If Zellij attachment fails after task preparation, reuse the task. It remains
  available through `--no-attach`.
- If a group tab request fails, inspect `tab-request.txt` and the opened tabs.
  Earlier members may still be running. Rerunning creates an entirely new group.
- If capture fails, inspect the session's `capture-error.txt` and saved turns.
  Do not claim that a missing response was captured or delete error markers
  merely to bypass a handoff failure.
- Read or search `events/` only for an explicitly assigned diagnostic analysis.
  Diagnostic events are not task context and cannot be passed with `--from`.

For requested deletion, run `fx delete <task-name>` from the project directory,
outside the target Zellij session. Zellij must be installed. Deletion stops the
session and removes the task, context, and captured results. Git branches remain.
Inspect source status and needed context first. Use `--force` only when loss
of uncommitted, untracked, ignored, or detached work is explicitly authorized.
Never use deletion as routine recovery for a failed launch.
