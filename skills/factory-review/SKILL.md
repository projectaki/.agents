---
name: factory-review
description: "Use only when the human explicitly starts the review lifecycle at any point after investigation, planning, or implementation and supplies a repository plus available context, artifacts, or review scope; run a four-cell Codex/Claude review matrix and return one numbered merged report without fixing findings."
disable-model-invocation: true
---

# Factory Review

Run an independent review of the context and repository state visible at the
time the human invokes this lifecycle. Review investigation findings, a plan,
implementation changes, or any combination the human provides.

## Input

Require:

- the repository or worktree to review
- the human's review request or scope
- any available context, investigation packet, plan, diff, implementation
  packet, verification evidence, or risk decisions

Use an explicit base, commit, diff, or file set when supplied. Otherwise inspect
the current branch, staged, unstaged, and untracked changes, and the available
thread context. If the target remains ambiguous, stop with the smallest question
needed to define it.

Before sending context to review CLIs, minimize it and redact secrets,
credentials, tokens, personal data, and sensitive production data.

## Review Matrix

Run one independent subagent for every model/role intersection:

| Review role | Codex 5.6 Sol High | Claude Fable 5 High |
|---|---:|---:|
| Bug finder | 1 | 1 |
| Regression reviewer | 1 | 1 |

This produces four review subagents:

1. Codex 5.6 Sol High × bug finder
2. Claude Fable 5 High × bug finder
3. Codex 5.6 Sol High × regression reviewer
4. Claude Fable 5 High × regression reviewer

Interpret “ensure no regressions” as the regression-reviewer role.

### Models

- Codex cells use `$codex-cli` with `gpt-5.6-sol` and high reasoning.
- Claude cells use `$claude-cli` with `claude-fable-5[1m]` and high effort.

Do not silently substitute another model. If a requested model is unavailable,
mark that cell failed.

### Roles

Bug finder:

- Find concrete correctness defects, broken invariants, unsafe error paths,
  concurrency problems, data corruption, security-relevant bugs, and behavior
  that contradicts the supplied context.
- Prefer demonstrable failures over stylistic concerns.

Regression reviewer:

- Find behavior that existing users, callers, integrations, data, or operations
  could lose because of the reviewed work.
- Check compatibility, edge cases, tests, migrations, performance, observability,
  rollback, and unchanged behavior outside the intended scope.

## Matrix Subagents

Use the host runtime's subagent mechanism. Spawn exactly one subagent for each
matrix cell. Request all four concurrently when capacity permits; if the host
has fewer child-agent slots, queue remaining cells and start them as soon as a
slot is free. Never collapse two cells into one subagent.

Each subagent must receive:

- exactly one matrix cell identifier and review role
- the same sanitized review scope and human-supplied context
- the repository or worktree path
- the cell output contract below
- an explicit instruction to use exactly one CLI skill

Use these assignments:

| Cell | Subagent instruction |
|---|---|
| Codex × bug finder | Use `$codex-cli`; run one `gpt-5.6-sol` high-reasoning review |
| Claude × bug finder | Use `$claude-cli`; run one `claude-fable-5[1m]` high-effort review |
| Codex × regression reviewer | Use `$codex-cli`; run one `gpt-5.6-sol` high-reasoning review |
| Claude × regression reviewer | Use `$claude-cli`; run one `claude-fable-5[1m]` high-effort review |

Tell every subagent:

```text
Use the assigned CLI skill to execute exactly one independent review cell.
The CLI response is the cell result. Do not review the work directly, invoke the
other CLI, spawn nested agents, edit files, merge findings, or inspect another
cell's output.
```

Wait for all four subagents before merging. Treat all cells as required. If
subagents are unavailable, a CLI skill reports unavailable, or a cell fails
once, report the matrix as incomplete. Do not install a CLI, change
authentication, seek elevated access, retry, or run the missing cell in the main
agent. An incomplete matrix cannot produce an `approve` verdict.

## Cell Output Contract

Require every cell to return findings only when it can explain:

- severity: `P0`, `P1`, `P2`, or `P3`
- concise title
- file and line, artifact section, or other precise location
- observed evidence and triggering conditions
- user or system impact
- smallest safe recommendation
- confidence: `high`, `medium`, or `low`

Require a cell with no findings to say so and identify what it inspected and any
remaining uncertainty. Treat access failures as missing evidence, not findings.

## Merge Workflow

After all four cells return:

1. Record the status of every matrix cell.
2. Normalize severity and discard unsupported speculation.
3. Merge findings that describe the same underlying issue. Preserve every cell
   that independently found or materially disagreed with it.
4. Keep distinct failure modes separate even when they touch the same code.
5. Assign stable report identifiers in severity order: `R001`, `R002`, `R003`,
   and so on. Every reported finding must have exactly one identifier.
6. Explain disagreements or low-confidence findings without manufacturing
   consensus.
7. Sanitize the merged report. Remove or secure raw temporary outputs and logs
   after merging unless the human requests retention.
8. Produce one report for the human.

## Output

Return:

- review scope and context used
- matrix status table for all four cells
- verdict: `approve`, `approve-with-findings`, `reject`, or `incomplete`
- numbered merged findings, ordered by severity
- for each finding: identifier, severity, title, location, evidence, impact,
  recommendation, confidence, and contributing matrix cells
- disagreements and discarded unsupported claims
- missing evidence, failed cells, and residual risk
- exact human decisions or follow-up requested

## Stop Condition

Stop when all four cells have completed or failed once and the numbered merged
report is complete. Return the report to the human. Do not fix findings, edit the
reviewed work, invoke another factory skill, or start another lifecycle.
