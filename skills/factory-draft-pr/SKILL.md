---
name: factory-draft-pr
description: "Create or update a GitHub draft PR after factory verification passes. Build a deterministic, plain-language description from the canonical task, analysis, change-assurance report, and verified evidence; map every regression concern to durable proof and validate the published body."
---

# Factory Draft PR

Publish 1 evidence-backed draft PR for the verified change. The PR description
is a reviewer document about the feature, not a development diary.

When orchestrated, the primary thread must delegate this skill to the routed
tier worker. That worker must not spawn another lifecycle actor.

## Inputs

Require repository, base and feature branches, the canonical task description
and scope, analysis handoff, approved plan, full base-to-head diff,
implementation packet, current implementation review, matching `pass`
verification, matching final `change-assurance-report.md`, and
reviewer-accessible URLs for required visuals. Local paths are not evidence.

The delivery assignment must name these mandatory PR sections in this order:
`Task`, `What changed`, `Concerns raised during analysis`,
`Regression assurance`, and `Gaps`.

## Workflow

1. Confirm repository, branches, auth, clean worktree, and exact verified head.
   Stop for uncommitted requested changes or mismatched verification.
2. Read all canonical task, scope, analysis, plan, implementation, diff,
   assurance, regression, evidence, and verification inputs. Never infer scope
   from commit messages alone.
3. Build an internal coverage ledger. Map every behavioral path, material
   analysis or review concern, acceptance criterion, and regression area to
   exactly 1 plain-language row in `Regression assurance`. A row may cover
   multiple internal records only when they describe the same behavior,
   affected surface, evidence, verdict, and residual risk.
4. Validate the ledger and description before remote writes. Stop for
   unaccounted diff, missing or duplicate mappings, unsupported claims, missing
   evidence, or unaccepted exceptions. Do not put internal IDs in the PR.
5. Push the verified head with tracking. Never force-push without an explicit
   request.
6. Convert inspection and automated evidence to durable permalinks containing
   the pushed SHA. Pair automated test code with its execution result.
7. Find an existing branch PR. If its body contains evidence mapping, reconcile
   every still-current entry into the new assurance rows. Preserve the evidence
   and meaning; do not erase traceability merely because the template changed.
8. Build the complete body with
   [assets/draft-pr-template.md](assets/draft-pr-template.md). Use the fixed
   section order and source rules below. Do not add optional sections.
9. Validate the body with:

   ```bash
   python3 <skill-directory>/scripts/validate-pr-description.py <body-file>
   ```

10. Update the existing PR or create a **draft** PR against the requested or
    default base.
11. Read the PR back through GitHub. Normalize line endings and one trailing
    newline, then compare the published body byte-for-byte with the validated
    body and re-run validation:

    ```bash
    python3 <skill-directory>/scripts/validate-pr-description.py \
      <published-body-file> --expected <validated-body-file>
    ```

    Reconcile the internal coverage ledger against the read-back body.
12. Report delivery success only when the draft state, exact body comparison,
    required sections, complete traceability, and evidence links all pass.
    Missing traceability is a delivery failure even when the branch was pushed
    and the PR exists.

## Content

### Task

Copy the canonical human task description and accepted scope. Preserve the
feature language and intent. Apply accepted clarifications, but do not replace
the task with a summary of the implementation. Demote embedded headings below
level 2 so the required top-level section order remains unchanged.

### What changed

Describe the final behavior in concise bullets. Include relevant compatibility
or migration work. Describe behavior, not file inventory or lifecycle history.

### Concerns raised during analysis

List every material feature, behavior, security, data, compatibility, or
operational concern from the canonical analysis and final-diff review. Use
plain descriptive names. Include concerns resolved by the implementation so
reviewers can find their proof in `Regression assurance`. Write `None.` only
when the canonical analysis and review contain no material concerns.

### Regression assurance

Use 1 compact row per distinct behavior at risk. Each row must state:

- behavior at risk
- affected user, API, component, system, contract, data, or operational surface
- automated, inspection, or manual evidence
- verdict
- residual risk or accepted waiver

Do not show path, risk, finding, acceptance-criterion, fingerprint, assignment,
or lifecycle IDs. Translate them to stable human descriptions.

For automated evidence, link the exact test assertions at the pushed SHA and
their matching current-head result. For inspection evidence, explain why the
change cannot cause the regression and link the relevant final code plus an
available corroborating signal. Use manual evidence only when automation cannot
prove the property, and link a sanitized reviewer-accessible artifact.

Every required row must have current evidence. An accepted waiver must identify
the residual risk and human decision. Missing, stale, failed, inaccessible, or
local-only evidence blocks delivery.

### Gaps

List only product-relevant work discovered during implementation or review and
explicitly left outside the task scope. Explain the user or system impact and
the intended follow-up when known. Write `None.` when there are no gaps.

Do not put failed checks, test-runner or environment startup problems, tool
availability, CI troubleshooting, upload problems, evidence collection limits,
agent constraints, or lifecycle commentary in `Gaps` or anywhere else in the
PR. A required evidence gap blocks delivery instead of becoming PR content.

## Writing and safety

- Use concise Markdown, plain language, and repository terms familiar to human
  reviewers. Trace every claim to the current diff, task, docs, or evidence.
- Describe only the verified head. Omit revision history, prior errors,
  superseded requirements, discarded approaches, agent lifecycle, worker
  assignments, model details, local machine state, and troubleshooting.
- Do not expose internal shorthand or IDs. Names such as “session expiry” are
  useful; labels such as `P14`, `R-7`, `AC3`, or `finding-F2` are not.
- Avoid duplication and secrets, tokens, private URLs, customer data, and
  troubleshooting details.
- Remove all template comments and placeholders before validation.
- Keep the PR draft unless explicitly asked to mark it ready.
- Do not stage, commit, amend, rebase, or otherwise change the verified head.
- Do not add visual evidence to the repository solely for the PR.
- Report remote checks separately; omit routine passing CI from the body.
