---
name: x-split-into-smaller-chunks
description: Split a large branch or pull request into a cohesive linear stack of smaller pull requests with an identical final tree.
---

- Inspect the full branch or pull request diff. Record the original head commit, target branch, and merge base. Preserve the original commit as the comparison reference.
- Group changes by purpose and dependency, not by file count or existing commits. Split changes within a file when needed.
- Aim for at most 20–30 changed files per pull request. Keep inseparable changes together and explain larger groups in their descriptions.
- Combine small, related changes when they make sense to review together. Avoid many tiny pull requests.
- Build one linear stack. The first pull request targets the original target branch. Each later pull request targets the preceding branch.
- Use GitHub's official [gh stack extension](https://github.com/github/gh-stack). Check its installed help. Install it with `gh extension install github/gh-stack` if needed. Use `gh stack init` and `gh stack add` to create the stack, then `gh stack submit` to publish it.
- Make each layer coherent and testable with its predecessors. Include its required tests and supporting changes. Do not depend on later layers.
- Preserve the original changes exactly. Do not introduce fixes, cleanup, or unrelated base updates while splitting.
- Before publishing, compare `git rev-parse '<tip>^{tree}'` with `git rev-parse '<original-head>^{tree}'`. Require identical tree identifiers. This verifies all tracked paths, file bytes, and modes. Resolve every mismatch before proceeding.
- Run relevant checks for each layer. Use the x-write-good-pr skill for each title and description. Explain what the layer contains, why the changes belong together, and its dependencies.
- Verify the published stack is linear and its tip still has the original tree. Report the ordered pull request links and verification results.
