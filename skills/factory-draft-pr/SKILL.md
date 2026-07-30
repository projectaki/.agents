---
name: factory-draft-pr
description: "Create or update a GitHub draft PR after factory verification passes. Map the complete diff to durable inspection, test, screenshot, video, or accepted-exception evidence."
---

# Factory Draft PR

Publish 1 evidence-backed draft PR for the verified change.

When orchestrated, the primary thread must delegate this skill to the routed
tier worker. That worker must not spawn another lifecycle actor.

## Inputs

Require repository, base and feature branches, criteria, full base-to-head diff,
implementation packet, current implementation review, matching `pass`
verification, matching final `change-assurance-report.md`, and
reviewer-accessible URLs for required visuals. Local paths are not evidence.

## Workflow

1. Confirm repository, branches, auth, clean worktree, and exact verified head.
   Stop for uncommitted requested changes or mismatched verification.
2. Read all task, scope, plan, implementation, commit, diff, assurance,
   regression, evidence, and verification inputs. Never infer scope from commit
   messages alone.
3. Validate complete change-path and acceptance-to-evidence maps before remote
   writes. Stop for unaccounted diff, unsupported paths or criteria, or
   unaccepted exceptions.
4. Push the verified head with tracking. Never force-push without an explicit
   request.
5. Convert inspection and automated evidence to durable permalinks containing
   the pushed SHA. Pair automated test code with its execution result.
6. Find an existing branch PR.
7. Rebuild its full title and body from current facts with
   [assets/draft-pr-template.md](assets/draft-pr-template.md). Existing PR text
   is replaceable content, not truth.
8. Update it or create a **draft** PR against the requested or default base.
9. Read it back. Confirm draft state, sections, and evidence links.

## Content

### Verified behavior

- Summarize behavior, not files or internal matrices.
- Keep stable IDs and grouped accounting internal. Link durable exhaustive
  detail only when reviewers need it; never link local reports.
- For simple non-behavioral or behavior-preserving work, give a concise
  inspection reason, final-code link, and available corroborating signal.
- Pair automated test code with its matching result.
- Use visuals only when automation cannot prove a static or sequential property.
- Show accepted exceptions and residual risk. Unaccepted exceptions block.

### Summary

- Describe the final diff in concise, related behavior bullets.
- Include relevant compatibility or migration work.
- Do not add separate `Why` or `User impact` sections.

### Acceptance criteria

- Account for every criterion exactly once across automated and exceptional
  visual evidence.
- Prefer unit, integration or contract, component, then end-to-end proof.
- Use 1 compact row per criterion unless distinct behaviors need distinct proof.
- Link exact test assertions at the pushed SHA and the matching result. Prefix
  with the level, such as `✅ [Unit: rejects expired tokens](<permalink>)`.
- Use tight GitHub line anchors and the smallest sufficient link set, ordered
  fastest to slowest and separated with `<br>`.
- Include only current-head passing criteria. Stop if automatable proof is
  missing; never substitute video or weaken criteria.

### Exceptional visuals

Include only criteria automation cannot prove. Require matching review
rationale and successful same-head verification. For each, state the behavior,
technical or perceptual limitation, and sanitized reviewer-accessible URL.
Use screenshots for static properties and video for sequences, gestures,
animation, timing, or transitions. Missing or inconvenient tests do not justify
visuals.

### Regression confidence and gaps

State `No regressions were observed in the verified scope.` only when verified.
Do not list routine CI or duplicate evidence.

List only unresolved product, behavior, code, security, data, or compatibility
gaps needing follow-up. Exclude CI, test output, warnings, environment or upload
problems, evidence limits, and agent constraints. Omit the section when empty.

## Writing and safety

- Use concise Markdown and repository language. Trace every claim to current
  diff, task, docs, or evidence.
- Describe only the verified head. Omit revision history, prior errors,
  superseded requirements, discarded approaches, and agent workflow.
- Avoid duplication and secrets, tokens, private URLs, customer data, and
  troubleshooting details.
- Keep the PR draft unless explicitly asked to mark it ready.
- Do not stage, commit, amend, rebase, or otherwise change the verified head.
- Do not add visual evidence to the repository solely for the PR.
- Report remote checks separately; omit routine passing CI from the body.
