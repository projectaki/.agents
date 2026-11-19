# x

My personal agent plugin. It holds my engineering principles and the workflows that I want an agent to follow on every task. It runs in Claude Code, Codex, and Cursor.

## Install it in Claude Code

The plugin is in the `amx-plugins` marketplace at the root of this repository.

1. Add the marketplace: `/plugin marketplace add projectaki/.agents`. For a local checkout, give the folder path instead: `/plugin marketplace add ~/.agents`.
2. Install the plugin: `/plugin install x@amx-plugins`.
3. Restart Claude Code. The skills show up as `x:<name>`.

To test changes to the plugin without installing it, start Claude Code with `claude --plugin-dir ~/.agents/x`.

## Start a task with `/x:go`

Type `/x:go` and then the task:

```
/x:go The export button on /reports downloads an empty CSV when a date filter is set. Repro: open localhost:3000/reports, choose "last 7 days", click Export.
```

The agent then does these steps:

1. It reads the adapter skill for its harness, for example `adapter-claude-code`. The adapter maps the general words in the skills, such as "background subagent", to that harness's tools.
2. It states your goal and the smallest change that it expects to meet it. Correct it here if it misread the task.
3. It reads `brain` and each principle whose condition fits the task.
4. It picks a playbook and copies the playbook's steps into its todo list.
5. It works through the steps. The main agent plans, reviews, and verifies. An `x-agent` subagent writes the code, so the agent that writes the code does not review it.
6. It opens a pull request from a worktree off `main`.
7. Its reply names each principle that changed a decision.

Put the place where the change runs and how to check it in the task text. Most playbooks start by reproducing or verifying on that place.

The agent does work that can be undone and then shows you the result. It asks before a force-push, deleted data, or a message to other people.

## Pick the playbook

`/x:go` picks the playbook from the task text. Each playbook is a file in `skills/go/playbooks/`.

| Task | Playbook | Example task text |
| --- | --- | --- |
| A question about how or why code works | `investigation` | How does token refresh work, and why is it in middleware? |
| A defect | `bug-fix` | Export gives an empty CSV with a date filter. Repro: ... |
| New or changed behavior | `feature` | Add per-user rate limits to the public API: 100 requests a minute, 429 with `Retry-After`. |
| New structure, same behavior | `refactoring` | Move the pricing logic out of `checkout.ts`. No behavior change. |
| A design choice that an experiment can settle | `prototype` | Sidebar or top tabs for the dashboard? Try both. |
| A change to this plugin | `authoring-a-skill` | Add a principle about retries to brain. |
| A test of whether a skill change changes agent behavior | `eval` | Does the new verify skill make agents take screenshots? |

Every playbook ends with `opening-a-pr`, except `investigation` and `prototype`, which change no shipped code. The PR step needs a git repository with a `main` branch and a logged-in `gh`.

## Other commands that you type

These skills run only when you type them:

- `/x:sharpen <task>` rewrites a vague task into a deeper one. Give its output to `/x:go`.
- `/x:talk-normally` restates the last reply in plain language.
- `/x:create-verification-skill` makes a project skill that drives your app the way a user does. Run it once for each project. The `verify` skill uses it before any other check.
- `/x:statechart` checks a TLA+ model of a flow and draws it.
- `/x:create-formal-verification-skill`, `/x:maintain-verification-skill`, and `/x:maintain-formal-verification-skill` set up and maintain project verification.

The other skills, such as `verify`, `architect`, `arena`, `interrogate`, `clean-text`, and `clean-code`, run when `/x:go` calls them or when the agent matches a request to their description. Each skill's `description` field says when it applies.

## Build your own workflow

`/x:go` runs a full workflow from a playbook. Playbooks run only through `/x:go`. To build your own workflow, call the skills and `brain` directly in the order that you want, for example `/x:how`, then `/x:architect`, then `/x:interrogate`. Each skill that starts subagents tells the agent to read the adapter for its harness first, so it works without `/x:go`.

Without `/x:go`, nothing applies the triggers in `skills/go/SKILL.md`. Ask for each step that you want, such as `clean-code` before a commit or `verify` after a UI change.

## Where things are

- `skills/go/SKILL.md` has the triggers and the playbook index. Rules about how the agent works go here.
- `skills/brain/SKILL.md` has the principle index. Rules about the code go in `skills/brain/principles/`.
- `skills/adapter-*/SKILL.md` has each harness's tools, models, and flags. No other file names them.
- `agents/x-agent.md` has the rules for each subagent that `/x:go` starts.
- `.claude-plugin/`, `.codex-plugin/`, and `.cursor-plugin/` have the manifest for each harness.

To change the plugin, run `/x:go` with the change. It uses the `authoring-a-skill` playbook. Check the result with `claude plugin validate ~/.agents/x`.

## Parts that are not finished

- `/x:go-env` cannot create task environments yet. The `x-env` skill is empty, and its command-line tool in `tools/x-env/` is in progress.
- The Cursor adapter is empty. In Cursor, the agent maps the capability words in `skills/go/references/capabilities.md` to its tools by itself.
- The `verify` skill names the `agent-browser`, `maestro-local-tests`, `tmux`, and `screenshot` skills, which are not in this plugin. Without them, `verify` uses a project verification skill or the tools that the session has.
