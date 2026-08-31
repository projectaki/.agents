---
name: factory-draft-pr
description: "Publish a supplied change package as a GitHub draft pull request. Build and validate a deterministic plain-language body, map every regression concern to durable evidence, push the supplied revision, and verify the published result."
---

# Factory Draft PR

## Purpose

Publish one evidence-backed draft pull request for the supplied change package.
The description is a reviewer document about the current feature. It is not a
development record.

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

## Inputs

Require:

- repository, base branch, feature branch, and exact change revision
- publication authority and draft-state policy
- canonical human task description and accepted scope
- final behavior and compatibility or migration details
- complete diff and change-assurance record for the supplied revision
- acceptance-proof record with claims, paths, risks, evidence, and waivers
- material concerns and review findings
- product-relevant gaps
- publication eligibility verdict for the supplied revision
- reviewer-accessible URLs for required visual evidence

The publication eligibility verdict must permit delivery. Every required proof
must have current evidence or an accepted waiver. Local paths are not reviewer
evidence. Stop when requested changes are uncommitted or the supplied revision
does not match the branch head.

## Operation

1. Confirm the repository, branches, authentication, clean worktree, exact
   revision, and publication authority.
2. Read every supplied input. Do not infer scope from commit messages.
3. Build an internal coverage ledger from the acceptance-proof and
   change-assurance records. Map each behavioral path, material concern,
   acceptance criterion, and regression area to one `Regression assurance` row.
   Combine records only when their behavior, affected surface, evidence,
   verdict, and residual risk are the same. Do not widen a waiver.
4. Compare the coverage ledger with the complete diff and all supplied
   evidence. Stop for an unaccounted change, missing or duplicate mapping,
   unsupported claim, unaccepted exception, or missing evidence.
5. Push the supplied revision with branch tracking. Do not force-push unless the
   human explicitly requests it.
6. Create durable evidence links that contain the pushed commit hash. Pair each
   automated test link with its current result link.
7. Find an existing pull request for the branch. Preserve each current evidence
   mapping when rebuilding its assurance rows.
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

12. Reconcile the coverage ledger with the published body. Return success only
    when the draft state, exact body, required sections, evidence links, and all
    mappings pass.

## Pull request content

Use these level-two sections once and in this order.

### Task

Copy the canonical human task description and accepted scope. Apply accepted
clarifications. Do not replace the task with an implementation summary. Demote
embedded headings below level two.

### What changed

Use concise bullets to describe the final behavior. Include relevant
compatibility or migration work. Do not list files or work history.

### Concerns raised during analysis

List each supplied material feature, behavior, security, data, compatibility,
or operational concern. Use descriptive names. Include resolved concerns so
reviewers can find their evidence. Write `None.` only when the supplied change
package contains no material concern.

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
Missing, stale, failed, inaccessible, or local-only evidence blocks publication.

### Gaps

List only supplied product work that remains outside the task scope. State its
user or system impact. State the intended follow-up when known. Write `None.`
when there are no gaps.

Do not use `Gaps` for failed checks, environment problems, tool limits, upload
problems, evidence limits, agent constraints, or work history. Required
evidence gaps block publication.

## Outputs

Return a structured result and a concise human summary with:

- status: `published` or `blocked`
- pull request URL and number
- base branch, feature branch, and published revision
- draft state and publication action
- exact validated body
- published-body read-back comparison and validation result
- coverage-ledger reconciliation result
- external checks reported separately from the pull request body
- blockers and residual risk

## Side effects

Push the supplied revision. Create or update one GitHub pull request. Read the
published result back through GitHub. Do not perform any other remote write.

## Failure results

Return `blocked` for missing authority, invalid or stale inputs, publication
conflicts, failed evidence validation, failed push, failed GitHub write, or
failed read-back comparison. A pushed branch without a valid published pull
request is not success.

## Safety and quality

- Trace every claim to the supplied diff, task, documentation, or evidence.
- Describe only the supplied revision. Exclude revision history, prior errors,
  discarded approaches, agent details, local machine state, and troubleshooting.
- Remove template comments and placeholders.
- Exclude secrets, tokens, private URLs, customer data, and duplicate text.
- Keep the pull request in draft state unless the human requests otherwise.
- Do not stage, commit, amend, rebase, or otherwise change the supplied revision.
- Do not add visual evidence to the repository only for the pull request.
- Report remote checks separately. Do not add routine successful continuous
  integration checks to the body.

## Non-goals

Do not implement, review, verify, merge, release, or change product files.
