---
name: x-split-into-smaller-chunks
description: Split a large branch or pull request into a cohesive linear stack of smaller pull requests with an identical final tree.
---

Inputs: Source branch or pull request, plus optional pull request description requirements.

- Inspect the full branch or pull request diff. Record the original head commit, target branch, and merge base. Preserve the original commit as the comparison reference.
- Use the [pull request size and grouping rules](../x-plan/SKILL.md#pull-request-size-and-grouping) on the actual diff. Use planned boundaries as a starting point when available. Group changes by purpose and dependency. Split changes within a file when needed.
- Combine small changes when they answer the same review question. Keep a cohesive change together if a split would make it harder to verify. Explain in the description why a larger behavior change belongs together.
- Build one linear stack. The first pull request targets the original target branch. Each later pull request targets the preceding branch.
- Use GitHub's official [gh stack extension](https://github.com/github/gh-stack). Check its installed help. Install it with `gh extension install github/gh-stack` if needed. Use `gh stack init` and `gh stack add` to create the stack, then `gh stack submit` to publish it.
- Make each layer coherent and testable with its predecessors. Include its required tests and supporting changes. Do not depend on later layers.
- Preserve the original changes exactly. Do not introduce fixes, cleanup, or unrelated base updates while splitting.
- Before publishing, compare `git rev-parse '<tip>^{tree}'` with `git rev-parse '<original-head>^{tree}'`. Require identical tree identifiers. This verifies all tracked paths, file bytes, and modes. Resolve every mismatch before proceeding.
- Run relevant checks for each layer. Use the [pull request writing skill](../x-write-good-pr/SKILL.md) for each title and description. Apply any description requirements supplied as input.
- Verify the published stack is linear and its tip still has the original tree. Report the ordered pull request links and verification results.
