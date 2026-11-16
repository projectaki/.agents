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
- **About to ask the user "which approach", "how should I", or "what should this do"** → First, classify the question. If running something can answer it, do not ask. Examples are behavior, timing, layout, output, and performance. Build a prototype with the **prototype** skill and let the result decide. If the task is a read-only investigation that delivers an answer with evidence, answer from the evidence and do not build an experiment. Ask the user only about a product or preference choice that no experiment can settle.
- **Any code** → First, state the data shape. Then choose how to organize the code according to the model-the-domain principle in the **brain** skill.
- **Code that crosses a function boundary** → Before you implement, run the **architect** skill.
- **Design or code bake-off** → Run the **arena** skill. Several models build the same design or code. Pick a base result and add the strong parts of the other results to it.
- **Contested design** → Before you ship, run the **interrogate** skill.
- **Any text** → Write and check it with the **clean-text** skill. This includes your replies, documents, plans, pull request descriptions, issues, commit messages, review comments, code comments, and skill files.
- **Before each commit** → Check the diff with the **clean-code** skill.
- **A change to a UI, an app, or a CLI** → Prove that it works in the real app with the **verify** skill. Show the evidence, such as a screenshot or the actual output. Passing tests alone are not proof. For a bug fix, reproduce the bug yourself in the same app before you fix it. Ask the user to reproduce it only when you cannot reach that app.
- **A review or comment on a pull request, from a person, a bot, or an agent** → Be skeptical. Many comments come from automated tools, even when a person posts them. Check each comment against the code, then fix it, dismiss it with a specific reason, or ask the user, according to the **triage-comments** skill. Do not change code only to make a comment go away.
- **A skill is broken during a task** → Report what is broken and why. Do not quietly work around it. Propose a fix to the skill and ask the user before you change it. Continue with the parts of the task that do not depend on that skill.
