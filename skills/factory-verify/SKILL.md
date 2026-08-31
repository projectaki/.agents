---
name: factory-verify
description: "Verify a supplied change revision against its requirements, behavioral paths, risks, proof obligations, review findings, and available evidence. Run the smallest missing checks and return a complete verification result without changing the implementation."
---

# Factory Verify

## Purpose

Determine whether the supplied change revision has sufficient current evidence.

## Inputs

Require:

- task contract and acceptance criteria
- impact analysis, behavioral paths, risks, and approved plan
- change revision and complete diff
- implementation result and change-assurance record
- independent review result for the supplied revision
- acceptance-proof record
- reproduction result when applicable
- available automated, inspection, manual, and visual evidence
- authority and capabilities to run missing non-mutating checks

Require the change-assurance record to identify its base, head, fingerprint,
change groups, and behavioral paths. Return `inconclusive` or `blocked` for a
missing, stale, or contradictory required input.

## Operation

1. Reconcile every diff group, behavioral path, acceptance criterion, and risk
   with evidence, review findings, and results for the same revision.
2. Run the smallest focused command that closes a missing or stale unit,
   integration, contract, interface, type, lint, build, or deterministic
   end-to-end proof gap. Do not run a broad suite when a focused command is
   sufficient. Do not install tools or create tests.
3. Accept visual evidence only for a risk that requires observation and only
   when its risk, path, and change revision match. Do not collect new visual
   evidence.
4. Treat missing, stale, failed, blocked, inaccessible, or inferred required
   evidence as unverified. Do not require video when automation proves the
   property.
5. Produce a complete finalized change-assurance record. Give every path a
   verdict and durable evidence. Inspection needs a concise reason and an
   available supporting signal. An exception remains blocked until the human
   accepts its residual risk.
6. Produce a complete finalized acceptance-proof record. Give every active
   claim and proof obligation an allowed verdict. Reject proof substitution,
   stale evidence, incomplete universal inventories, and exceptions outside
   their exact claim and path.

## Outputs

Return a structured result and a concise human summary with:

- verdict: `pass`, `fail`, `inconclusive`, or `blocked`
- verified behavior and acceptance-criterion results
- regression risks and evidence gaps
- checks run, their source, scope, result, and exact revision
- supplied results distinguished from checks run during this operation
- visual evidence and why automation was insufficient
- review findings and remaining risk
- complete finalized change-assurance record
- complete finalized acceptance-proof record

Use `pass` only when the complete diff, every path and criterion, and every
material risk have current evidence or a human-accepted exception. Use `fail`
when a criterion, required check, or required observed workflow fails. Mark
remote continuous integration as `pending`. State “no regressions observed in
the verified scope.” Never state that regressions are impossible.

Keep identifiers, fingerprints, and full mappings in the structured result.
Use plain behavior, risk, and check names in the human summary.

## Side effects

Start permitted local environments and run non-mutating evidence checks. Do not
change product, test, configuration, or documentation files.

## Failure results

Return `inconclusive` when required evidence is missing, stale, or inaccessible.
Return `blocked` when the operation cannot proceed safely or access a
requirement.

## Non-goals

Do not fix the change, create tests, collect new visual evidence, publish, merge,
or release.
