---
name: factory-review
description: "Use only when the human explicitly starts the review lifecycle with a repository and review scope. Run the required four-cell Codex/Claude bug and regression review matrix, then return one numbered merged report without fixing findings."
disable-model-invocation: true
---

# Factory Review

Run four independent reviews and merge their evidence.

## Need

The repository or worktree, review scope, and available context such as packets,
plans, diffs, verification evidence, or risk decisions. Use a supplied base,
commit, diff, or file set; otherwise inspect all current changes. Ask one small
question if the target remains ambiguous.

Minimize and sanitize context before sending it to review CLIs.

## Matrix

Spawn exactly one subagent for each cell, concurrently when capacity permits:

| Cell | CLI and model | Role |
|---|---|---|
| Codex bug | `$codex-cli`, `gpt-5.6-sol`, high reasoning | Bug finder |
| Claude bug | `$claude-cli`, `claude-fable-5[1m]`, high effort | Bug finder |
| Codex regression | `$codex-cli`, `gpt-5.6-sol`, high reasoning | Regression reviewer |
| Claude regression | `$claude-cli`, `claude-fable-5[1m]`, high effort | Regression reviewer |

Bug finders seek demonstrable correctness, invariant, error-path, concurrency,
data, security, and context violations. Regression reviewers seek losses in
compatibility, edge cases, tests, migrations, performance, observability,
rollback, and behavior intended to remain unchanged.

Give every subagent the same sanitized scope and context, its one cell, the
repository path, and this instruction:

```text
Use the assigned CLI skill for exactly one independent review cell. Return the
CLI result. Do not review directly, use another CLI, spawn agents, edit files,
merge findings, or inspect another cell.
```

Require each cell to report only supported findings with severity `P0`–`P3`,
title, precise location, evidence and trigger, impact, smallest safe
recommendation, and confidence. A no-findings result must state what was
inspected and what remains uncertain.

Do not substitute models, retry a failed cell, install CLIs, change auth, seek
elevated access, or replace a cell in the main session. Any missing cell makes
the matrix `incomplete` and prevents `approve`.

## Merge

1. Record every cell's status.
2. Discard unsupported claims and merge findings with the same root cause;
   preserve contributing cells and disagreements.
3. Keep distinct failure modes separate.
4. Order by severity and assign one ID per finding: `R001`, `R002`, …
5. Sanitize the report and remove or secure temporary outputs.

## Return

- scope and context reviewed
- four-cell status table
- verdict: `approve`, `approve-with-findings`, `reject`, or `incomplete`
- numbered findings with severity, location, evidence, impact, recommendation,
  confidence, and contributing cells
- disagreements, discarded claims, missing evidence, residual risk, and human
  follow-up

## Stop

Return the merged report after every cell completes or fails once. Do not fix
findings or start another lifecycle.
