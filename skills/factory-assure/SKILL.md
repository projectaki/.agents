---
name: factory-assure
description: "Independently assure either a Factory implementation plan or an exact committed software change. Review the complete subject, run the smallest missing non-mutating checks, and return a revision-bound verdict."
---

# Factory Assure

## Purpose

Provide independent plan or change assurance without fixing the subject.

## Inputs

Require the task contract, triage result, behavioral paths, risks, proof
obligations, current assurance record, bounded subject, and assurance kind:
`plan` or `change`. For change assurance, also require the exact clean committed
revision, complete base-to-head diff, and implementation result.

The assurer must not be the implementer.

## Operation

1. Reconcile the complete subject with the task revision and accepted scope.
2. Trace each plan step or diff group through callers, consumers, data,
   permissions, side effects, integrations, and observable behavior.
3. Find unsupported assumptions, omitted paths, scope growth, proof gaps, and
   direct or adjacent regression risks.
4. For plan assurance, approve only when the plan is implementable and every
   material path and risk has sufficient planned proof.
5. For change assurance, inspect every diff group and run only the smallest
   missing or stale non-mutating checks. Bind every result to the exact commit.
6. Collect sanitized visual evidence only when automation cannot prove a
   required visual property.
7. Accept an exception only when the human approved its exact criterion, path,
   and residual risk.
8. Finalize the assurance record without weakening required proof.

## Outputs

Return:

- assurance kind and verdict
- for a plan: `approve`, `reject`, `needs-input`, or `blocked`
- for a change: `pass`, `fail`, `needs-input`, or `blocked`
- exact subject and revision
- findings with severity, location, evidence, impact, correction, and confidence
- every acceptance criterion, path, risk, diff group, and evidence verdict
- checks run during assurance, supplied evidence, gaps, and residual risk
- complete finalized assurance record

Use `pass` only for a clean committed revision with complete current evidence
or exact human-accepted exceptions. State that no regressions were observed in
the verified scope. Never claim that regressions are impossible.

## Side effects

Read sources, start permitted local environments, run non-mutating checks, and
create sanitized evidence artifacts when required. Do not change repository or
remote-system state.

## Failure results

Return `needs-input` for a material decision or exception. Return `blocked` for
missing, stale, contradictory, or inaccessible required evidence.

## Non-goals

Do not implement, fix, commit, push, publish, merge, release, or approve your
own work.
