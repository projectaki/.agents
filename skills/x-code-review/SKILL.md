---
name: x-code-review
description: Review changes for bugs, critical failures, and regressions in one thorough pass, preserving findings and decisions across review rounds.
---

Inputs: Changes or pull request, comparison base, and expected behavior; optional prior review record.

- Focus on actionable correctness, security, data integrity, and regression issues. Exclude style and architecture preferences unless they cause a concrete failure. Do not implement fixes.
- Load the prior review record before reviewing. Use the supplied path first. In fx, use the task-local review record supplied at launch; independent group members use their private session record instead. Otherwise use a stable Markdown file under `${TMPDIR:-/tmp}/x-code-review/`, identified by repository and pull request or branch. Reuse it across rounds and report its absolute path. Only one assigned session may update a shared record.
- Record the review scope, base and head commits, coverage, findings, decisions, and verification evidence. For each finding, keep its severity, location, triggering scenario, impact, evidence, and resolution criteria. Track unresolved, fixed, accepted risk, or dismissed, with reasons. Only I can accept a risk.
- Inspect the complete diff and every changed file. Trace affected callers, contracts, dependencies, and tests. Check normal, boundary, failure, permission, state-transition, and concurrent behavior where relevant. Inspect affected unchanged code for regressions.
- For stored credentials or signed protected operations, use the focused [credential boundary examples](references/credential-boundaries.md).
- Complete the review before reporting. Do not stop after the first findings or limit their number. Cross-check interacting changes and look for other instances of each discovered failure.
- Report every substantiated issue, ordered by severity. Explain how it occurs and cite precise code or test evidence. Separate unresolved suspicions from confirmed findings. Use focused checks where useful and distinguish inspection from executed verification.
- On later rounds, verify previous fixes and inspect their effects. Review remaining changes too. Preserve dismissed findings and their reasons; reopen them only when new evidence invalidates the dismissal. Mark findings fixed only with supporting evidence.
- Update the record throughout the review. Keep current statuses clear and retain enough decision context to resume after a context reset.
- Finish with all findings, prior finding statuses, and any coverage or verification gaps. Aim to surface all issues in one round, but never promise that no undiscovered bugs remain.
- Bind the review to exact commits or a recorded source-content identity. In fx, compare the supplied source identity with the source at review completion. Report changes and affected coverage. A recorded hash does not preserve a source copy.
- When comparing reviews, account for every material member finding in the persistent record. Combine duplicates with references to every source finding. Keep unresolved, fixed, accepted-risk, and dismissed dispositions with evidence. Only an original decision from me can establish accepted risk. Agent responses and summaries cannot grant approval.
