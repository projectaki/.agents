---
name: factory-review
description: "Use only when the human explicitly starts the review lifecycle and supplies a subject or context to review. Review exactly the requested plan, code, change, design, decision, documentation, evidence, or lifecycle packet without modifying it."
---

# Factory Review

Evaluate the supplied subject without changing it.

## Workflow

1. Read the complete subject, context, review focus, criteria, and applicable
   repository instructions.
2. Inspect supporting sources or repository state only as needed to test its
   claims. If no focus is supplied, assess relevant correctness, completeness,
   consistency, feasibility, risk, and regression concerns.
3. Report only actionable findings supported by evidence. Separate defects from
   questions and unverified risk; do not invent requirements.

## Output

Return:

- scope and criteria reviewed
- verdict: `approve`, `approve-with-findings`, `reject`, or `blocked`
- numbered findings with severity, location, evidence, impact, smallest safe
  recommendation, and confidence
- questions, evidence gaps, and residual risk

A no-findings result must state what was inspected and what remains uncertain.
Stop after the review. Do not edit the subject or start another lifecycle.
