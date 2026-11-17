---
name: go
description: Entry point for my way of working. Applies my principles and routes the task to the right workflow. Use for /x:go.
disable-model-invocation: true
---

# Go

## Non-negotiables

- In each reply, name each principle that shaped a decision. State the specific choice that it changed.
- Before your first decision, read the **brain** skill at `../brain/SKILL.md` from this file. Then read each principle file that applies to the task.
- Name only principles whose file you read in this session.

## Triggers

- **Your first message on a task** → In your own words, state the user's goal and the problem that they solve. If the task ships a change, also state the smallest change that you expect to meet the goal. Do not wait for confirmation. If the evidence shows that the requested change is wrong or not necessary, show the evidence and stop. Restate the goal in each subagent brief, at the start of the `## Why` section of each pull request, and at the start of each final report, including your final reply. Skip this for a fully specified one-line edit.
- **About to ask the user "which approach", "how should I", or "what should this do"** → First, classify the question. If running something can answer it, do not ask. Examples are behavior, timing, layout, output, and performance. Build a prototype with the Prototype playbook and let the result decide. If the task is a read-only investigation that delivers an answer with evidence, answer from the evidence and do not build an experiment. Ask the user only about a product or preference choice that no experiment can settle.
- **Any code** → First, state the data shape. Then choose how to organize the code according to the model-the-domain principle in the **brain** skill.
- **TypeScript code, or a new TypeScript project** → Follow the **typescript** skill.
- **Code that crosses a function boundary** → Before you implement, run the **architect** skill.
- **Design or code bake-off** → Run the **arena** skill. Several models build the same design or code. Pick a base result and add the strong parts of the other results to it.
- **Contested design** → Before you ship, run the **interrogate** skill.
- **Any text** → Write and check it with the **clean-text** skill. This includes your replies, documents, plans, pull request descriptions, issues, commit messages, review comments, code comments, and skill files.
- **Before each commit** → Check the diff with the **clean-code** skill.
- **A change to a UI, an app, or a CLI** → Prove that it works in the real app with the **verify** skill. Show the evidence, such as a screenshot or the actual output. Passing tests alone are not proof. For a bug fix, reproduce the bug yourself in the same app before you fix it. Ask the user to reproduce it only when you cannot reach that app.
- **A review or comment on a pull request, from a person, a bot, or an agent** → Be skeptical. Many comments come from automated tools, even when a person posts them. Check each comment against the code, then fix it, dismiss it with a specific reason, or ask the user, according to the **triage-comments** skill. Do not change code only to make a comment go away.
- **A skill is broken during a task** → Report what is broken and why. Do not quietly work around it. Propose a fix to the skill and ask the user before you change it. Continue with the parts of the task that do not depend on that skill.
- **About to hand work to another agent** → Choose a background subagent or a visible session with the delegation reference.
- **The context fills up: large tool output, long files, repeated reads, or work planned for many subagents** → Send bulk work to subagents. Keep summaries in the main conversation, not raw output. Limit the files and turns for each phase.
- **About to ask "should I do X?" about work that can be undone** → Do it. Then show the result and the reason. This does not apply to a deviation from a standard. For that, follow the approval reference. Ask before an action that cannot be undone, such as a force-push, deleting data, or sending a message to other people.
- **You write the same instruction a second time, or the user corrects the same behavior twice** → Propose a mechanism in the x plugin, such as a script or a check that a skill runs. Do not propose more text. If no mechanism can enforce the rule, propose to make the instruction easier to find and to add an example of the mistake. Ask the user before you change a skill.

## References

Each reference is a file in `references/` next to this file. Read a reference when its condition applies.

- [Approval for exceptions](references/approval-for-exceptions.md): read before you deviate from a standard, use a temporary workaround, or build on an uncertain design.
- [Delegation](references/delegation.md): read before you hand work to another agent.
- [File search](references/file-search.md): read before you search files in a git repository.

## Playbooks

Match the task to a playbook below. Before you add any steps of your own, copy every step of the playbook into your todo list, word for word. Keep each step that you do not do in the list, with a one-line `skip: <reason>`.

- [Investigation](playbooks/investigation.md): a read-only question, such as how X works, why Y was built this way, whether we are sure about Z, or whether to do X or Y.
- [Feature](playbooks/feature.md): new or changed behavior, built from a named data shape.
- [Bug fix](playbooks/bug-fix.md): a reported defect to reproduce, find the root cause of, and fix with runtime evidence.
- [Refactoring](playbooks/refactoring.md): a change to structure or shape that keeps behavior the same, such as a rename, extract, inline, dedupe, or move.
- [Prototype](playbooks/prototype.md): a throwaway sketch that makes a design or behavior decision cheaply, or settles an open question by observing it.
- [Authoring a skill](playbooks/authoring-a-skill.md): writing or changing a skill, a principle, a reference, or a playbook in the x plugin.
- [Opening a PR](playbooks/opening-a-pr.md): run at the end of every other playbook.

If no playbook matches, say so in your first message. If the task is clear enough to do, continue with the triggers and the **brain** principles. If it is not, ask the user what steps to follow.
