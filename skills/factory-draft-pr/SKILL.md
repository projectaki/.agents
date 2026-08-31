---
name: factory-draft-pr
description: "Create or update a GitHub draft PR after factory verification passes. Build a deterministic, plain-language description from the canonical task, analysis, change-assurance report, and verified evidence; map every regression concern to durable proof and validate the published body."
---

# Factory Draft PR

Publish one evidence-backed draft pull request for the verified change. The
description is a reviewer document about the current feature. It is not a
development record.

When orchestrated, the primary thread must delegate this skill to the selected
worker. That worker must not delegate the lifecycle work again.

## Human communication

Write all human-facing text in ASD-STE100 Simplified Technical English.

- Use short sentences.
- Use the active voice.
- Put one idea in each sentence.
- Define each term when you first use it.
- Do not use a code, ticket number, short label, or internal identifier alone.
  Give its plain-language meaning each time.
- Do not invent labels for findings.
- Do not use metaphors, idioms, or figures of speech.
- Rewrite text that is not clear before you publish or report it.
- Say when you cannot explain something in plain words.

## Required inputs

Require all of these inputs:

- repository, base branch, and feature branch
- canonical task description and accepted scope
- analysis handoff and approved plan
- full diff from the base branch to the verified head
- implementation packet and current implementation review
- matching successful verification
- matching final `change-assurance-report.md`
- reviewer-accessible URLs for required visual evidence

Local paths are not reviewer evidence. Stop if requested changes are
uncommitted or the verified commit does not match the branch head.

## Workflow

1. Confirm the repository, branches, authentication, clean worktree, and exact
   verified head.
2. Read every required input. Do not infer scope from commit messages.
3. Build an internal coverage ledger from the verified proof ledger. Map each
   behavioral path, material concern, acceptance criterion, and regression area
   to one `Regression assurance` row. Combine records only when their behavior,
   affected surface, evidence, verdict, and residual risk are the same.
   Do not widen a waiver.
4. Compare the ledger with the full diff and all input evidence. Stop for an
   unaccounted change, a missing or duplicate mapping, an unsupported claim, an
   unaccepted exception, or missing evidence.
5. Push the verified head with branch tracking. Do not force-push unless the
   human explicitly requests it.
6. Create durable evidence links that contain the pushed commit hash. Pair each
   automated test link with its result link.
7. Find an existing pull request for the branch. Preserve each current evidence
   mapping when you rebuild its assurance rows.
8. Build the complete body with
   [assets/draft-pr-template.md](assets/draft-pr-template.md). Do not add
   top-level sections.
9. Validate the body:

   ```bash
   python3 <skill-directory>/scripts/validate-pr-description.py <body-file>
   ```

10. Update the existing pull request or create a draft pull request against the
    requested or default base branch.
11. Read the pull request through GitHub. Compare the published body with the
    validated body and validate it again:

    ```bash
    python3 <skill-directory>/scripts/validate-pr-description.py \
      <published-body-file> --expected <validated-body-file>
    ```

12. Reconcile the coverage ledger with the published body. Report success only
    when the draft state, exact body, required sections, evidence links, and all
    mappings pass.

When the orchestrator supplies Factory telemetry context, record push and pull
request operations, failures, retries, fallbacks, and read-back checks with the
best-effort writer. Telemetry failure does not change delivery status.

## Pull request content

Use these level-two sections once and in this order.

### Task

Copy the canonical human task description and accepted scope. Apply accepted
clarifications. Do not replace the task with an implementation summary. Demote
embedded headings below level two.

### What changed

Use concise bullets to describe the final behavior. Include relevant
compatibility or migration work. Do not list files or lifecycle history.

### Concerns raised during analysis

List each material feature, behavior, security, data, compatibility, or
operational concern from the analysis and final review. Use descriptive names.
Include resolved concerns so reviewers can find their evidence. Write `None.`
only when both sources contain no material concern.

### Regression assurance

Use one compact row for each distinct behavior at risk. Each row must state the
behavior, affected surface, evidence, verdict, and residual risk or accepted
waiver.

Do not show internal path, risk, finding, acceptance criterion, fingerprint,
assignment, or lifecycle identifiers. Use stable human descriptions.

- Automated evidence must link the exact test at the pushed commit and its
  current result.
- Inspection evidence must explain why the regression cannot occur. It must
  link the final code and an available supporting signal.
- Manual evidence is permitted only when automation cannot prove the behavior.
  It must explain why and link a sanitized, reviewer-accessible artifact.

An accepted waiver must identify the residual risk and the human decision.
Missing, stale, failed, inaccessible, or local-only evidence blocks delivery.

### Gaps

List only product work that the team discovered during implementation or review
and explicitly left outside the task scope. State its user or system impact.
State the intended follow-up when known. Write `None.` when there are no gaps.

Do not use `Gaps` for failed checks, environment problems, tool limits, upload
problems, evidence limits, agent constraints, or lifecycle text. Required
evidence gaps block delivery.

## Safety and quality

- Trace every claim to the current diff, task, documentation, or evidence.
- Describe only the verified head. Exclude revision history, prior errors,
  discarded approaches, agent details, local machine state, and troubleshooting.
- Remove template comments and placeholders.
- Exclude secrets, tokens, private URLs, customer data, and duplicate text.
- Keep the pull request in draft state unless the human requests otherwise.
- Do not stage, commit, amend, rebase, or otherwise change the verified head.
- Do not add visual evidence to the repository only for the pull request.
- Report remote checks separately. Do not add routine successful continuous
  integration checks to the body.
