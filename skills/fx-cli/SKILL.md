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
Reasoning defaults to high. `--new-tab` requires an existing Zellij session.
This command supplies its own assignment and session name. It does not create
or reopen the selected task. `analyze` is a reserved task action name.

Each run writes `evidence-inventory.json` and its own `findings.md` under
`context/analyses/<number>-analyze-<model>/`. Normal response capture preserves
the final report. The assignment requires full log coverage in bounded chunks,
detailed sequences, exact citations, and explicit unread ranges. It traces
later defects through planning, implementation, reviews, discovery, and proof.
It covers memory failures, crashes, retries, recovery, and instruction conflicts.
Recommendations must identify a concrete project or Factory change and how to
validate it. The assignment permits writing only its own report and notes.
Normal provider permissions still apply; this is not a filesystem sandbox.

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
an existing Zellij session. Each new launch creates a new conversation and a numbered context directory
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

## Resume a Claude conversation

Use the original session directory printed at launch:

```bash
fx agent claude --resume context/000001-review-claude-opus-5-5
```

Replace the example with the actual directory. Paths resolve from the invoking
directory and must stay inside this task's context. Absolute paths also work.
`--new-tab` is supported in Zellij. Do not combine resume with `--name`, `--prompt`,
`-r`, or `--from`. Resume supports Claude; other providers need their own
`agents/<agent>.resume` handler. Group members and comparison or analysis sessions
can be resumed by their own session directories.

Resume preserves the model, reasoning, original instructions, settings, findings,
and starting context. It appends callback events and captures new responses in
the same session. Each resumed launch gets its own native debug log under
`events/claude-debug-resume-<unique-id>.log`; original logs remain unchanged.
It does not resend the initial assignment or allocate a new context directory.

Fx reads the conversation identifier from its recorded Claude hook events or
response metadata. A startup event is enough to resume before the first response.
Missing or conflicting identifiers and partial callback tails stop resume.
The provider's local conversation history must still exist. Fx does not guess
the latest conversation or reconstruct deleted history from diagnostic logs.
Claude launches now hold a session lock. A duplicate launch fails while the
session runs. Exit sessions launched before this support was installed first.

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
Codex captures main-conversation `Stop` hooks; notifications never publish answers.
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
