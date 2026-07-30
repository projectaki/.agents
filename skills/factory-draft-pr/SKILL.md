---
name: factory-draft-pr
description: "Create or update a GitHub draft pull request after factory verification passes. Use when asked to publish a Factory change with the complete diff grouped into behavioral paths and every path mapped to durable inspection, automated-test, screenshot, video, or explicitly accepted exception evidence."
---

# Factory Draft PR

Publish one evidence-backed draft PR for the verified change.

## Input

Require the repository, base branch, feature branch, acceptance criteria, full
base-to-head diff, implementation packet, current `$factory-regression-scope`
packet, and a matching `$factory-verify` packet with verdict `pass`. Require a
matching final-revision `change-assurance-report.md` and a reviewer-accessible
URL for every required screenshot or video; local paths are not evidence.

## Workflow

1. Confirm the repository, base branch, current branch, authentication, clean
   worktree, and exact verified head. Stop if requested changes are uncommitted
   or the verification packet covers a different head or diff.
2. Inspect the task context, test scope, plan, implementation packet, commits,
   complete diff, regression scope, evidence results, and verification packet.
   Do not infer scope from commit messages alone.
3. Build and validate the complete change-path and acceptance-to-evidence maps
   before changing remote state. Stop if any diff region is unaccounted for,
   any path or criterion lacks acceptable proof, or any exception lacks
   explicit human acceptance.
4. Push the exact verified head with tracking. Never force-push unless the user
   explicitly requests it.
5. Convert inspection and automated evidence to durable code or test-code
   permalinks containing the pushed head SHA. Include the matching automated
   execution result.
6. Check whether the branch already has a PR and choose update or create.
7. Rebuild the complete title and body from the current task, final diff, and
   verified evidence using
   [assets/draft-pr-template.md](assets/draft-pr-template.md). Treat an existing
   PR title or body only as content to replace, not as a source of truth.
8. Update the existing PR title/body, or create a **draft** PR against the
   requested or default base branch.
9. Read the created/updated PR back from GitHub and verify that it remains a
   draft and the rendered body has exactly the intended sections and evidence
   links.

## Content rules

### Change-path assurance

- Give reviewers a compact plain-language behavior summary rather than a
  file-by-file narrative or internal assurance matrix.
- Account for the complete diff through stable path IDs and grouped change
  regions internally. In the PR, name each behavior directly and do not expose
  internal IDs. Use an existing durable reviewer-accessible accountability link
  only when a reviewer genuinely needs the exhaustive detail. Never link a
  local report.
- For simple non-behavioral or behavior-preserving work, include one concise
  inspection reason, a final-code link, and an available corroborating signal.
- For automated evidence, link the exact test code and its matching execution
  result. A test permalink alone does not prove that it passed for this head.
- Use reviewer-accessible screenshot or video links only when automation cannot
  sufficiently prove the relevant static or sequential property.
- Show accepted exceptions and residual risk prominently. An unaccepted
  exception blocks PR creation.

### Summary

- Describe what the final diff actually changes.
- Group related implementation work into concise reviewer-oriented bullets.
- Include important compatibility or migration work when it is part of the diff.
- Do not add separate `Why` or `User impact` sections.

### Acceptance criteria fulfilled

- Account for every acceptance criterion exactly once across the automated and
  exceptional-video tables.
- Put a criterion in the automated table whenever deterministic automation can
  prove it. Prefer the fastest sufficient evidence in this order: unit,
  integration or contract, component, then end-to-end.
- Use one compact row per criterion with specification area, required behavior,
  and automated evidence. Split a criterion only when its behaviors require
  materially different proof.
- Render every automated item as a descriptive link to the exact test function
  or assertion in the pushed head commit, prefixed by its level, for example
  `✅ [Unit: rejects expired tokens](<permalink>)`, followed by a link to the
  matching execution result.
- Use durable GitHub blob permalinks containing the head commit SHA and tight
  line anchors. Do not substitute implementation code, an execution dashboard,
  a local path, or unverifiable prose for inspected test assertions. The
  execution-result link complements the test-code link.
- Use the smallest sufficient set of links. When multiple tests are necessary,
  order them from fastest to slowest and separate them with `<br>`.
- Include only criteria demonstrably fulfilled and passed for the current head.
  If an automatable criterion lacks a passing test, stop and report unfinished
  test work instead of substituting video.
- State observable behavior rather than a file inventory. Do not invent or
  weaken acceptance criteria to make the table complete.

### Exceptional screenshot or video evidence

- Include this section only when at least one acceptance criterion cannot be
  sufficiently proven with deterministic automated assertions.
- Require the regression-scope packet to explain why automation is
  insufficient and the verification packet to record a successful observation
  for the same risk and head.
- Use one compact row per exceptional criterion with specification area,
  required behavior, the reason automation is insufficient, and a descriptive
  link to the sanitized reviewer-accessible screenshot or video.
- Use screenshots for static visual properties and video for sequences,
  gestures, animation, timing, or state transitions. Never use visual evidence
  merely because a test is slow, inconvenient, missing, or was not
  implemented. Never include local paths, credentials, private data, or
  placeholder links.

### Regression confidence

- Include `No regressions were observed in the verified scope.` only when the
  matching verification packet supports it.
- Do not list routine CI jobs or duplicate acceptance evidence.

### Known gaps

- Include only unresolved business-logic, product-behavior, code, security, data, or compatibility gaps that may require follow-up.
- Exclude CI status, test output, dependency warnings, formatting warnings, environment problems, evidence limitations, upload limitations, and agent/tooling constraints.
- Omit the section when no genuine implementation gap is known.
- Do not manufacture a gap merely to fill the section.

## Writing rules

- Use concrete, concise Markdown and the repository's domain language.
- Keep every claim traceable to the diff, task context, documentation, or verification evidence.
- Present the PR as a snapshot of the current verified head. Inputs provide
  facts; their commentary and chronology are not PR content.
- Do not mention earlier PR descriptions, previous revisions, review
  iterations, prior mistakes, corrected misunderstandings, superseded
  requirements, discarded approaches, or agent workflow.
- State the resulting behavior and current constraints directly. Include
  history only when the final diff itself introduces a compatibility or
  migration fact that reviewers must act on.
- Do not duplicate the same fact across sections unless its regression implication needs explanation.
- Do not expose credentials, tokens, private URLs, customer data, or internal troubleshooting details.
- Default to a draft PR. Mark it ready only when the user explicitly asks.

## Safety

- Do not stage, commit, amend, rebase, or otherwise change the verified head.
- Do not store screenshot or video evidence in the repository solely to attach it to a PR.
- Report remote checks separately after opening the PR; do not copy routine passing CI results into the description.
