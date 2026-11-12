---
name: x-write-good-pr
description: Write concise pull request titles and descriptions that explain why a change matters, show where to start reviewing, and link to evidence for important claims.
---

Inputs: Changes, feature requirements, and evidence; optional design notes and description requirements.

- Read the full diff and relevant surrounding code. For a stack, read the diff against the preceding branch. Identify the problem, resulting behavior, key design decisions, and material risks directly from the inputs.
- Write a specific title. Use my voice and describe the current implementation without relying on chat history.
- Keep claims within what the evidence proves. Label inferences and uncertainties. Ask for missing decision rationale instead of inventing it. Omit unsupported assertions.
- Link to the task or design decision when it helps explain why the change exists. Link directly to the code, test, or other evidence that supports an important claim. Use the revision the reviewer needs to inspect. For prior behavior, use the original code or a regression test shown to fail before the fix.

## Length and selection

- Aim for a brief the reviewer can scan before opening the diff. A few sentences may be enough. Give complex changes more space when needed to explain correctness, design, or deployment safety.
- Lead with what changes and why. Include a short example only when it makes the behavior easier to understand.
- Explain only the implementation choices whose reasons are not clear from the diff. Keep the reason beside the choice. Omit routine wiring, file inventories, pattern names, and step-by-step code narration unless they explain a material constraint.
- Omit what the hosting platform already shows beside the description: title, branches, stack or dependency order, position in a series, related pull requests, linked tickets, commits, changed files, reviewers, labels, and check status. Do not add navigation sections, position labels such as "part 2 of 4", or lists of related pull requests. Mention another pull request or ticket only when its content explains this change, and then state that content.
- State each fact once. Combine related decisions. Link existing documentation for extended mechanics instead of copying it into the description. Do not move excess text into an optional-reading section.
- Keep essential security rules, compatibility limits, known coverage gaps, approved exceptions, and required operational actions visible when they apply. Describe concrete risks rather than listing generic possibilities.
- Put evidence beside the claim it supports. Point to the test or result that demonstrates a key behavior or exposes a material gap. Leave routine check results in continuous integration.

## Description structure

Use only the sections the change needs. Simple descriptions do not need headings.

1. **Summary**. Explain the problem and resulting behavior in one short paragraph. For a stack, state what this pull request delivers on its own.
2. **Where to start**. For a change across files, give a short reading order when it helps the reviewer follow the behavior. Start with the most important decision, entry point, or regression test. Link directly to the relevant code and follow the related changes in the order needed to understand them. State the main question the reviewer should verify. For a larger generated, documentation-only, or mechanical change, identify what needs close inspection, what can be skimmed, and how to check it. For a larger behavior change, explain why the pieces belong together.
3. **Key decisions**. Explain important choices whose reasons are unclear from the diff.
4. **Risks and rollout**. Include when there are concrete production risks, compatibility constraints, migrations, configuration changes, deployment steps, or rollback requirements. State defaults and any action required to activate the behavior. This applies to application changes as well as infrastructure changes.
5. **Screenshots**. Include for user interface changes. Add placeholders naming each screen, state, and action to capture and upload. Do not imply missing screenshots exist.

Before finishing, reread the description as a reviewer. Remove repetition, details the diff already explains, and information the platform already shows. Confirm that the reader can identify what changes, why the key choices matter, and what needs special care.
