---
name: x-understand-large-module
description: Explain a large pull request's purpose, code organization, and module boundaries so I can assess its design and review it.
---

Inputs: Pull request or changes and relevant context.

- Read the pull request, full diff, and relevant surrounding code and tests. Explain the problem and intended result first.
- Group changed files by responsibility. Explain why each group exists, where it belongs, and how it connects to the existing system.
- Focus on module boundaries: public interfaces, inputs, outputs, dependencies, state ownership, and failure handling. Trace one representative flow across them.
- Explain the design choices and tradeoffs that matter for review. Separate documented reasons from your inferences. Identify plausible alternatives and what they would change.
- Skip internal implementation details unless they affect behavior, correctness, a module boundary, or a design tradeoff. State what can be skipped and why.
- Build the explanation in small steps, one responsibility or boundary at a time. Use focused file references and a simple diagram when helpful. Let my questions guide deeper detail.
- Finish with the key design decisions I should assess and any unresolved questions. Do not change the code.
