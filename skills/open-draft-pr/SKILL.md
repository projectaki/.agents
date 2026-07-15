---
name: open-draft-pr
description: Create or update a GitHub draft pull request with the team's review-focused description template. Use when asked to open, prepare, publish, or rewrite a draft PR and its description should explain the implemented changes, fulfilled acceptance criteria, user-facing regression confidence, evidence, and genuine remaining product or code gaps.
---

# Open Draft PR

Create a draft PR that tells reviewers what changed, which discovered requirements are now satisfied, which test scenarios were added, and why affected user behavior is unlikely to regress.

## Workflow

1. Confirm the repository, base branch, current branch, authentication, and worktree state.
2. Inspect the task context, exploration findings, plan, documentation, commits, and complete base-to-head diff. Do not infer scope from commit messages alone.
3. If unpublished changes belong to the requested scope, stage explicit paths, commit using repository conventions, and run the relevant validation before pushing. Never include unrelated changes.
4. Push the current feature branch with tracking. Never force-push unless the user explicitly requests it.
5. Check whether the branch already has a PR:
   - Update its title/body when it exists.
   - Otherwise create a **draft** PR against the requested or default base branch.
6. Build the body from [assets/draft-pr-template.md](assets/draft-pr-template.md) using the rules below.
7. Read the created/updated PR back from GitHub and verify that it remains a draft and the rendered body has exactly the intended sections.

## Content rules

### Summary

- Describe what the final diff actually changes.
- Group related implementation work into concise reviewer-oriented bullets.
- Include important compatibility or migration work when it is part of the diff.
- Do not add separate `Why` or `User impact` sections.

### Acceptance criteria fulfilled

- Recover the criteria identified during exploration, planning, documentation, tests, and implementation.
- Include only criteria demonstrably fulfilled by the final implementation.
- State observable behavior, authorization boundaries, validation/error contracts, data isolation, and compatibility requirements where relevant.
- Describe outcomes, not a file-by-file implementation inventory.
- Do not invent acceptance criteria to make the section appear complete.

### Test cases added

- Split the section into `Frontend` and `Backend` subsections. Keep both headings; write `None` when a side has no added tests.
- Inspect the base-to-head test diff and include one bullet for every test case added by the PR.
- Translate test names and assertions into concise, user-readable scenarios describing the starting condition, action, and expected outcome.
- Expand parameterized tests into separate bullets when each input represents a distinct user role, permission, state, or business scenario.
- Include newly added unit, integration, component, service, and end-to-end cases. Exclude pre-existing tests changed only for formatting, fixture compilation, or setup compatibility.
- Do not include pass counts, CI results, filenames, method names, or implementation details unless needed to understand the scenario.
- Cross-check the final bullet count against the added executable cases so none are omitted or duplicated.

### No-regression confidence

- Identify the existing user behaviors and product areas touched by the change.
- Explain why each remains safe: exercised acceptance flow, preserved contract, unchanged path, compatibility layer, focused automated coverage, or equivalent evidence.
- Write from the user's perspective. Mention tests only as supporting rationale, never as a pass-count matrix.
- Include the concise conclusion `No regressions were observed in the verified scope.` only when supported by verification.
- Do not add a general `Verification` section or list CI jobs; reviewers can see CI separately. The `Test cases added` section describes coverage intent, not execution status.

### Evidence

- Leave the section empty for manual screenshot/video upload unless the user explicitly asks to populate it.
- Never describe upload failures, authentication limitations, local artifact paths, or evidence tooling in the PR body.

### Known gaps

- Include only unresolved business-logic, product-behavior, code, security, data, or compatibility gaps that may require follow-up.
- Exclude CI status, test output, dependency warnings, formatting warnings, environment problems, evidence limitations, upload limitations, and agent/tooling constraints.
- Leave the section empty when no genuine implementation gap is known.
- Do not manufacture a gap merely to fill the section.

## Writing rules

- Use concrete, concise Markdown and the repository's domain language.
- Keep every claim traceable to the diff, task context, documentation, or verification evidence.
- Do not duplicate the same fact across sections unless its regression implication needs explanation.
- Do not expose credentials, tokens, private URLs, customer data, or internal troubleshooting details.
- Default to a draft PR. Mark it ready only when the user explicitly asks.

## Safety

- Stop before staging or committing when the worktree contains changes whose ownership or scope is unclear.
- Do not store screenshot or video evidence in the repository solely to attach it to a PR.
- Report remote checks separately after opening the PR; do not copy routine passing CI results into the description.
