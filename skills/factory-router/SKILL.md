---
name: factory-router
description: "Use only when the human explicitly asks to route a factory task. Read the current thread and supplied context, determine the single next lifecycle stage, and return only that stage without performing it."
---

# Factory Router

Choose the next lifecycle from existing context. Do not perform lifecycle work.

## Route

Select the earliest unmet stage whose output is required. Skip a stage when its
result is already established by the thread, regardless of whether the stage
was formally run. If later evidence invalidates an earlier result, route back
to the earliest affected stage.

- `factory-context`: planning lacks essential issue, codebase, or documentation
  evidence. Skip for a small task already clear and grounded.
- `factory-replicate`: a reported failure needs a trustworthy pre-change
  baseline.
- `factory-plan`: context is sufficient but no accepted implementation-ready
  plan exists, including when findings invalidate the plan.
- `factory-implement`: an accepted plan exists and implementation is incomplete.
- `capture-pr-evidence`: UI changes are complete but current PR evidence is
  missing or stale.
- `factory-review`: the supplied subject needs review, confidence is explicitly
  insufficient, or an implementation is complete and unreviewed. Review may
  target any context, including a plan, change, decision, or evidence packet.
- `factory-verify`: implementation, applicable UI evidence, and review are
  complete, but required verification is not.
- `factory-learn`: completed work may contain durable, actionable knowledge that
  has not been assessed for preservation.
- `complete`: no lifecycle work remains.

Prefer `capture-pr-evidence` before reviewing completed UI work. Route rejected
or materially outdated artifacts back to the stage that must replace them.
Do not infer completion from elapsed effort or an agent's unsupported claim.

## Output

Return exactly one stage name from the list above and nothing else.
