---
name: x-plan
description: Create a reviewable implementation plan after triage when a software change needs design work. Use for consequential choices about module boundaries, interfaces, permissions, data, or recovery. A small change that follows an established pattern can use the triage handoff.
---

# Plan implementation

Start from the agreed scope, success criteria, and triage findings. Keep product code unchanged during planning.

1. Read applicable repository guidance. Apply relevant language and framework skills before choosing the design. Inspect the affected code and reuse established patterns.
2. Draft the smallest design that meets the task. Name the affected modules, their responsibilities, and their interactions. Cover relevant failure paths, compatibility, and recovery.
3. Resolve evidence gaps through investigation. Use the [open-question skill](../x-resolve-open-questions/SKILL.md) for decisions that need user input. Return to triage if requirements or scope change.
4. Run the [design quality skill](../x-ensure-quality/SKILL.md) on the draft. Revise the plan to address material findings. Keep the plan pending while a blocking decision or finding remains.

## Output

Produce one plan with the chosen design, ordered implementation steps, and a check for each success criterion and material risk. For larger changes, show the proposed directory tree and use short code examples or diagrams where they clarify contracts or flows.

In fx, save the plan in the session directory and link it from the handoff.
