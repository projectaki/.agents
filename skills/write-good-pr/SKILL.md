---
name: write-good-pr
description: Write pull request titles and descriptions that explain the purpose, module boundaries, and design decisions reviewers need to understand.
---

- Read the full diff and relevant surrounding code. Use the understand-large-module skill to identify responsibilities, module boundaries, and important design choices.
- Write a specific title. Use my voice and describe the current implementation without relying on chat history.
- Structure the description in the order below. Omit sections that do not apply. Do not include a validation section, local test results, or repeated continuous integration results.

## Description structure

1. **Overview:** Explain what the pull request implements and the problem it solves.
2. **Key concepts and boundaries:** Cover each added or materially changed concept, module boundary, and entry point that reviewers must understand. Explain what it is, why it exists, and how it connects to the system. Include relevant alternatives and rejection reasons only when supported by evidence. Do not invent decision history.
3. **Review guidance:** Suggest a reading order with focused file references. Identify design decisions that need particular attention.
4. **Implementation details (optional reading):** Explain internal choices that can change without affecting the important boundaries or behavior. Keep correctness, security, and public behavior in the main explanation.
5. **Screenshots:** Include for user interface changes. Add placeholders naming each screen, state, and action to capture and upload. Do not imply missing screenshots exist.
6. **Affected production behavior and potential regressions:** Include only when changing code already deployed to production. Describe the affected behavior, reach of the change, and plausible regressions.
7. **Compatibility and rollout:** Include only for infrastructure changes. Explain relevant compatibility constraints, migrations, configuration, deployment order, and rollback requirements.
