---
name: x-write-good-pr
description: Write pull request titles and descriptions that explain the feature, implementation, and reasons for each design decision with supporting evidence.
---

Inputs: Changes, feature requirements, and evidence; optional design notes and description requirements.

- Read the full diff and relevant surrounding code. Identify responsibilities, module boundaries, important concepts, and design decisions directly from the inputs.
- Write a specific title. Use my voice and describe the current implementation without relying on chat history.
- Support each factual claim with a reference beside it: relevant code lines, a test, a focused code snippet, or other direct evidence. Use links reviewers can access and the code version that proves the claim. For prior behavior, cite the original code or a regression test shown to fail before the fix.
- Keep claims within what the evidence proves. Label inferences and uncertainties. Ask for missing decision rationale instead of inventing it. Omit unsupported assertions.
- Structure the description in the order below. Omit sections that do not apply. Do not include a validation section, local test results, or repeated continuous integration results.

## Description structure

1. **Overview:** Give a detailed explanation of the feature or changed behavior. Explain who uses it, what they can now do, how it behaves, and the problem it solves. Include a concrete example when useful. Make it understandable without reading the code.
2. **Key concepts, boundaries, and implementation:** Cover each added or materially changed concept, module boundary, and entry point. Explain what it is, why it exists, how it was implemented, and how it connects to the system. Describe the main execution or data flow. For each concept, explain the design decisions, why the selected approach fits, and how it improves the code. Name patterns and structural choices explicitly, including choices such as Strategy or a static utility function. Explain relevant tradeoffs and alternatives only when supported by evidence. Group repeated decisions without omitting their rationale.
3. **Review guidance:** Suggest a reading order with focused file references. Identify design decisions that need particular attention.
4. **Implementation details (optional reading):** Explain lower-level mechanics and their rationale. Keep the main implementation approach and decisions affecting correctness, security, or public behavior in the main explanation.
5. **Screenshots:** Include for user interface changes. Add placeholders naming each screen, state, and action to capture and upload. Do not imply missing screenshots exist.
6. **Affected production behavior and potential regressions:** Include only when changing code already deployed to production. Describe the affected behavior, reach of the change, and plausible regressions.
7. **Compatibility and rollout:** Include only for infrastructure changes. Explain relevant compatibility constraints, migrations, configuration, deployment order, and rollback requirements.
