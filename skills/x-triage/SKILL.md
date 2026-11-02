---
name: x-triage
description: Investigate a software task before implementation. Report readiness for automatic implementation or all unresolved gaps that require human input.
---

# Task triage

Input: A task and available project context.
Output: A concise report with exactly one classification: AUTO (automatic implementation) or HIL (human in the loop).

Investigate only. Do not implement the task or change external state.

## Investigation

- Read applicable project guidance and relevant code, documentation, callers, dependencies, and tests.
- Confirm the problem exists. Check whether the task is already complete or duplicates existing work. Reproduce reported bugs when practical.
- Establish the goal, scope, exclusions, and observable success criteria. Separate facts, assumptions, and unknowns.
- Assess affected users, behavior, shared interfaces, data, compatibility, and recovery. Consider relevant security and operational risks. Assess impact separately from change size.
- Identify the simplest compliant approach. Check required access, dependencies, and unresolved product or architecture decisions.
- Map each success criterion and material risk to automated verification or existing evidence. Inspect whether checks detect relevant failures. Identify coverage limits and test maintenance costs.
- Resolve gaps through focused investigation and safe checks where practical. Expand only when evidence requires it. Stop when further investigation needs human input or disproportionate effort. Explain that limit.

## Decision

- **AUTO — automatic implementation:** The goal and scope are clear. Evidence supports a compliant approach. Adequate automated verification is feasible. No material gap or required human decision remains. High impact alone does not prevent this classification.
- **HIL — human in the loop:** At least one material gap remains. This includes missing requirements, evidence, access, or approval, and verification that is insufficient or disproportionately complex.

Do not use a numerical readiness score. Passing tests alone does not establish adequate coverage. Never present planned checks as completed evidence.

Automatic readiness permits the next implementation stage within existing authority. It does not grant merge, deployment, or production access. Completion requires the planned checks to pass.

## Report

Keep detail proportional to the task. Make the report self-contained:

1. **Decision:** Classification, brief reason, and recommended action. If evidence shows no change is needed, recommend closure without changes.
2. **Task:** Goal, scope, and success criteria.
3. **Evidence and impact:** Relevant file references, findings, assumptions, affected behavior, and regression risks.
4. **Approach and verification:** Proposed implementation, checks for each criterion and material risk, coverage limits, and recovery where relevant. Distinguish completed checks from planned checks.
5. **Human input:** For human involvement, list every identified unresolved gap. For each, state the consequence, automatic resolution considered, why it is insufficient, and the exact input or decision needed. Recommend a resolution when supported.

After new input, reassess and replace obsolete report content. Human input alone does not establish readiness. Repeat triage if scope or affected code changes materially, or implementation invalidates an important assumption.
