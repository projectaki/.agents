---
name: factory-draft-pr
description: "Publish one independently assured Factory change as a GitHub draft pull request. Push the exact clean commit, create or update the draft, and verify the published result."
---

# Factory Draft PR

## Purpose

Publish the requested exact revision as one verified draft pull request.

## Inputs

Require the aligned task contract, repository and branches, exact clean commit,
push and draft-pull-request authority, final assurance verdict, current
assurance record, final behavior, material risk, and reviewer-accessible
evidence links.

Stop when change assurance did not pass, the worktree is dirty, the branch head
differs from the assured commit, or required evidence is local-only.

## Operation

1. Confirm repository, authentication, branches, clean worktree, exact head,
   authority, and passing assurance.
2. Build a concise body from
   [the draft pull request template](assets/draft-pr-template.md). Describe only
   the current change. Do not include Factory process history.
3. Map each material behavior at risk to evidence, verdict, and residual risk.
4. Validate the body:

   ```bash
   python3 <skill-directory>/scripts/validate-pr-description.py <body-file>
   ```

5. Push without force. Create or update one draft pull request.
6. Read the published title, body, draft state, branches, and revision back from
   GitHub. Compare the body with the validated source and validate it again.

Write published text in the developer's first-person singular voice when it
describes their actions, decisions, ownership, or requests. Keep neutral facts
direct. Use ASD-STE100 Simplified Technical English.

## Outputs

Return:

- status: `published` or `blocked`
- pull request URL, number, branches, and exact revision
- created or updated action and draft state
- exact validated body and read-back result
- evidence mapping result, external checks, blockers, and residual risk

## Side effects

Push the exact supplied commit. Create or update one GitHub draft pull request.
Make no other local or remote change.

## Failure results

Return `blocked` for missing authority, stale inputs, a dirty or different
revision, missing evidence, push failure, publication failure, or read-back
mismatch. A pushed branch without a valid draft pull request is not success.

## Non-goals

Do not edit, stage, commit, amend, rebase, force-push, merge, release, or change
product files.
