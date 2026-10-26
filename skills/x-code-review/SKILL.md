---
name: x-code-review
description: Review changes for bugs, critical failures, and regressions in one thorough pass, preserving findings and decisions across review rounds.
---

Inputs: Changes or pull request, comparison base, and expected behavior; optional prior review record.

- Focus on actionable correctness, security, data integrity, and regression issues. Exclude style and architecture preferences unless they cause a concrete failure. Do not implement fixes.
- Load the prior review record before reviewing. Use a supplied path or a stable Markdown file under `${TMPDIR:-/tmp}/x-code-review/`, identified by repository and pull request or branch. Reuse it across rounds and report its absolute path.
- Record the review scope, base and head commits, coverage, findings, decisions, and verification evidence. For each finding, keep its severity, location, triggering scenario, impact, evidence, and resolution criteria. Track open, fixed, accepted risk, or not an issue, with reasons. Only I can accept a risk.
- Inspect the complete diff and every changed file. Trace affected callers, contracts, dependencies, and tests. Check normal, boundary, failure, permission, state-transition, and concurrent behavior where relevant. Inspect affected unchanged code for regressions.
- Complete the review before reporting. Do not stop after the first findings or limit their number. Cross-check interacting changes and look for other instances of each discovered failure.
- Report every substantiated issue, ordered by severity. Explain how it occurs and cite precise code or test evidence. Separate unresolved suspicions from confirmed findings. Use focused checks where useful and distinguish inspection from executed verification.
- On later rounds, verify previous fixes and inspect their effects. Review remaining changes too. Preserve dismissed findings and their reasons; reopen them only when new evidence invalidates the dismissal. Mark findings fixed only with supporting evidence.
- Update the record throughout the review. Keep current statuses clear and retain enough decision context to resume after a context reset.
- Finish with all findings, prior finding statuses, and any coverage or verification gaps. Aim to surface all issues in one round, but never promise that no undiscovered bugs remain.
