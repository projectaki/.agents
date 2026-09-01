---
name: factory-implement
description: "Implement a supplied approved plan in a scoped repository or worktree. Add targeted tests, account for the complete working diff, run reachable focused checks, and return implementation and assurance results."
---

# Factory Implement

## Purpose

Implement only the supplied approved plan.

## Inputs

Require an approved plan, repository or worktree, acceptance criteria, required
decisions, behavioral paths, risks, acceptance-proof record, proof requirements,
and mutation authority. Require a reproduction result for a bug fix. Stop before
editing when a required input is missing.

## Operation

1. Confirm mutation authority and inspect Git status. Preserve existing user
   changes.
2. Implement the approved scope with repository patterns. Avoid unrelated
   refactors. Keep domain logic out of infrastructure. Apply the repository's
   developer-voice rules to approved prose in documentation, comments,
   messages, and other developer-authored files. Keep neutral technical text
   factual. Use first-person singular voice only when the text refers to the
   developer's actions, decisions, opinions, ownership, or requests.
3. Add the smallest useful tests mapped to supplied risks. Add a practical
   regression test for a deterministic bug.
4. Build a complete change-assurance record. Group the whole working diff. Map
   every group to behavioral paths or a precise non-behavioral classification.
   Record current evidence.
5. Run reachable targeted checks.
6. Attach current evidence to the acceptance-proof record without changing the
   required or planned proof method.
7. Return the implementation result and all remaining proof work.

Investigate failed checks. Treat unrun checks as unknown. Report inaccessible
required checks. If evidence invalidates the plan, stop and return the required
plan decision instead of expanding scope.

For an optional tool, check availability once and try once. Do not install a
tool or seek elevated access only to run it. Do not repeat a failed operation
with unchanged preconditions unless the failure can be transient. State why a
retry is justified and what changed.

## Outputs

Return a structured result and a concise human summary with:

- status: `complete`, `needs-input`, or `blocked`
- changed files and behavior
- complete working-diff accountability in a change-assurance record
- tests mapped to supplied risks
- commands, results, and exact covered revision or diff
- complete updated acceptance-proof record
- skipped checks, fallbacks, uncovered risks, and residual risk
- unimplemented scope, unresolved risks, and required decisions
- current readiness facts without a lifecycle recommendation

Keep internal identifiers, fingerprints, and exhaustive mappings in the
structured result. Use plain behavior names in the human summary. Describe only
the current state. Mention plan divergence only when it leaves active scope,
risk, or a decision.

## Side effects

Modify approved product, test, configuration, migration, and documentation
files. Start permitted local environments. Run builds, tests, static analysis,
and other targeted checks. Do not write to remote systems unless the inputs
grant that authority.

## Failure results

Return `needs-input` for a plan-invalidating decision or missing authority.
Return `blocked` for an inaccessible required dependency or check.

## Non-goals

Do not expand scope, perform independent review, or claim final verification.
