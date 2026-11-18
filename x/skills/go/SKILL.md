---
name: go
description: Entry point for my way of working. Applies my principles and routes the task to the right workflow. Use for /x:go.
disable-model-invocation: true
---

# Go

## Non-negotiables

- Before any other step, read the adapter skill for the harness that you run in: `../adapter-claude-code/SKILL.md`, `../adapter-codex/SKILL.md`, or `../adapter-cursor/SKILL.md` from this file. If none matches, use the [capabilities](references/capabilities.md) with the tools that you have, and say so.
- In each reply, name each principle that shaped a decision. State the specific choice that it changed.
- Before your first decision, read the **brain** skill at `../brain/SKILL.md` from this file. Then read each principle file that applies to the task.
- Name only principles whose file you read in this session.

## Triggers

- **Your first message on a task** → In your own words, state the user's goal and the smallest change that you expect to meet it. Then continue. Start each subagent brief, the `## Why` section of each pull request, and each final report with the goal.
- **A question that running something can answer** → Do not ask the user. Settle it with the Prototype playbook. Ask the user only about a product or preference choice that no experiment can settle.
- **Code** → First, state the data shape. Code that crosses a function boundary → the **architect** skill. A bake-off → the **arena** skill. A contested design → the **interrogate** skill before you ship. TypeScript → the **typescript** skill.
- **Any text, your reply included** → the **clean-text** skill.
- **Before each commit** → the **clean-code** skill.
- **A change to a UI, an app, or a CLI** → the **verify** skill. For a bug fix, reproduce the bug yourself in the same app before you fix it.
- **Review comments on a pull request** → the **triage-comments** skill.
- **A skill is broken during a task** → Do not work around it quietly. Report what is broken, propose a fix, and ask the user before you change the skill. Continue with the parts that do not depend on it.
- **About to hand work to another agent** → the delegation reference.
- **The context fills up** → Send bulk work to subagents, and keep only summaries in the main conversation.
- **About to ask "should I do X?" about work that can be undone** → Do it, then show the result and the reason. Ask before an action that cannot be undone, such as a force-push, deleting data, or a message to other people. A deviation from a standard follows the approval reference.
- **The same instruction a second time, or the same correction twice** → Propose a mechanism in the x plugin, such as a script or a check, not more text. Ask the user before you change a skill.

## References

Each reference is a file in `references/` next to this file. Read a reference when its condition applies.

- [Approval for exceptions](references/approval-for-exceptions.md): read before you deviate from a standard, use a temporary workaround, or build on an uncertain design.
- [Capabilities](references/capabilities.md): read before you write or change a skill in the x plugin.
- [Delegation](references/delegation.md): read before you hand work to another agent.
- [File search](references/file-search.md): read before you search files in a git repository.

## Playbooks

Match the task to a playbook below. Copy its steps into your todo list before any steps of your own.

- [Investigation](playbooks/investigation.md): a read-only question, such as how X works, why Y was built this way, whether we are sure about Z, or whether to do X or Y.
- [Feature](playbooks/feature.md): new or changed behavior, built from a named data shape.
- [Bug fix](playbooks/bug-fix.md): a reported defect to reproduce, find the root cause of, and fix with runtime evidence.
- [Refactoring](playbooks/refactoring.md): a change to structure or shape that keeps behavior the same, such as a rename, extract, inline, dedupe, or move.
- [Prototype](playbooks/prototype.md): a throwaway sketch that makes a design or behavior decision cheaply, or settles an open question by observing it.
- [Authoring a skill](playbooks/authoring-a-skill.md): writing or changing a skill, a principle, a reference, or a playbook in the x plugin.
- [Eval](playbooks/eval.md): a blind test of whether a variant, such as a skill change, changes what agents do.
- [Opening a PR](playbooks/opening-a-pr.md): run at the end of every other playbook.

If no playbook matches, say so in your first message. If the task is clear enough to do, continue with the triggers and the **brain** principles. If it is not, ask the user what steps to follow.
