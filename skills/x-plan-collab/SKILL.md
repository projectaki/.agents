---
name: x-plan-collab
description: Design a new feature or larger software change with the user after triage, then create a reviewable implementation plan. Use when the user wants to make design decisions together before the plan is drafted.
---

# Plan implementation collaboratively

Start from the agreed scope, success criteria, and triage findings. Keep product code unchanged during planning.

1. Read applicable repository guidance. Apply relevant language and framework skills before choosing the design. Inspect the affected code and reuse established patterns.
2. Work through the [collaborative design phase](#collaborative-design) with the user.
3. Draft the smallest design that meets the task. Name the affected modules, their responsibilities, and their interactions. Cover relevant failure paths, compatibility, and recovery.
4. Resolve evidence gaps through investigation. Use the [open-question skill](../x-resolve-open-questions/SKILL.md) for decisions that need user input. Return to triage if requirements or scope change.
5. If the work has several purposes or is likely to exceed the review size target, propose pull request boundaries before implementation. State the purpose, dependencies, and verification for each proposed pull request. Check that each can be verified and safely merged with its predecessors.
6. Run the [design quality skill](../x-ensure-quality/SKILL.md) on the draft. Revise the plan to address material findings. Keep the plan pending while a blocking decision or finding remains.

## Collaborative design

- Read and follow the [terminal response skill](../nice-terminal-response/SKILL.md) when presenting decisions to the user.
- Identify the design decisions and their dependencies. Start with a decision that affects later choices. Investigate facts in the repository before asking the user.
- Discuss one decision at a time before drafting the design. Explain the relevant evidence, viable options, their consequences, and your recommendation. Include decisions for which you already have a preferred answer. Keep field inventories, feature flags, and test counting rules in the plan unless they affect the current decision.
- Involve the user in decisions about architecture, service and module boundaries, models, and code organization. Show how the affected parts fit together. For each proposed service or module, explain its purpose, responsibilities, callers, and dependencies. For each proposed model, explain what it represents, its key fields and relationships, and the rules it enforces.
- Show the proposed directory tree for the part under discussion before asking the user to agree. Use repository-relative paths and mark each file to add or change. Explain what code belongs in each file, why it belongs there, and what it depends on. Show how calls or data move between files when that helps explain the design. Update the tree as decisions are made.
- Wait for explicit agreement before moving on. Record the choice and its reason as each decision is made. Continue until each decision is agreed or explicitly deferred by the user. Keep the plan pending if a deferred decision blocks implementation.
- Draft the design from the agreed decisions. If later planning or design review introduces a new design decision or requires changing an agreed one, discuss it with the user before revising the design.

## Pull request size and grouping

- Aim for about 100 changed lines or fewer in a pull request that changes behavior. Count additions plus deletions, including tests and hand-written supporting changes. For a cohesive change, 100–300 lines is reasonable. Above 300 lines, look for a coherent split. Keep changes together when a split would make the behavior harder to verify. Keep the tests that prove the change with the behavior they cover.
- Group generated types and other generated output, documentation-only updates, and mechanical edits by purpose. Give them separate pull requests when each can be verified and safely merged on its own or with its predecessors. These pull requests can be larger when the reviewer can readily verify the generator, the documentation scope, or the mechanical operation. Apply the usual review scrutiny to refactors whose behavior is difficult to verify.
- When generated output must land with its source change, keep both in one pull request. Put the generated output in a separate commit and report its line count separately from the changes that count toward the target.

## Output

Produce one plan with the chosen architecture, service and model responsibilities and dependencies, ordered implementation steps, and a check for each success criterion and material risk. Include the agreed directory tree with the purpose of each file to add or change. Use short code examples or diagrams where they clarify contracts or flows.

In fx, save the plan in the session directory and link it from the handoff.
