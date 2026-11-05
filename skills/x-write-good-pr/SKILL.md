---
name: x-write-good-pr
description: Write concise pull request titles and descriptions that help reviewers understand the behavior, key design decisions, and material risks.
---

Inputs: Changes, feature requirements, and evidence; optional design notes and description requirements.

- Read the full diff and relevant surrounding code. Identify the problem, resulting behavior, key design decisions, and material risks directly from the inputs.
- Write a specific title. Use my voice and describe the current implementation without relying on chat history.
- Keep claims within what the evidence proves. Label inferences and uncertainties. Ask for missing decision rationale instead of inventing it. Omit unsupported assertions.
- Link evidence where it helps reviewers assess a non-obvious claim, security constraint, or important decision. Use focused references to the code version that proves the claim. For prior behavior, use the original code or a regression test shown to fail before the fix. Do not attach a citation to every sentence or repeat the same reference.

## Length and selection

- Aim for 150–300 words for a typical description. Small changes may need only a few sentences. Complex changes may need more space, but each extra detail must help a reviewer assess correctness, design, or deployment safety. Never remove a critical constraint to meet the word target.
- Lead with the problem and resulting behavior. Include a short example only when it makes the behavior easier to understand.
- Explain only the implementation choices whose reasons are not clear from the diff. Keep the reason beside the choice. Omit routine wiring, file inventories, pattern names, and step-by-step code narration unless they explain a material constraint.
- State each fact once. Combine related decisions. Link existing documentation for extended mechanics instead of copying it into the description. Do not move excess text into an optional-reading section.
- Keep essential security rules, compatibility limits, known coverage gaps, approved exceptions, and required operational actions visible when they apply. Describe concrete risks rather than listing generic possibilities.
- Do not include a validation section, local test results, or repeated continuous integration results. Mention test coverage only when it explains an important guarantee or gap.

## Description structure

Use only the sections the change needs. Simple descriptions do not need headings.

1. **Summary:** One short paragraph explaining the problem and resulting behavior. Make it understandable without reading the code.
2. **Key decisions:** A few short bullets covering the important implementation choices and their reasons. Include a focused file reference or review question only when it helps direct attention to a difficult or risky part.
3. **Risks and rollout:** Include when there are concrete production risks, compatibility constraints, migrations, configuration changes, deployment steps, or rollback requirements. State defaults and any action required to activate the behavior. This applies to application changes as well as infrastructure changes.
4. **Screenshots:** Include for user interface changes. Add placeholders naming each screen, state, and action to capture and upload. Do not imply missing screenshots exist.

Before finishing, reread the description as a reviewer. Remove repetition and details the diff already explains. Confirm that the reader can identify what changes, why the key choices matter, and what needs special care.
