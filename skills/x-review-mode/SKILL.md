---
name: x-review-mode
description: Apply supplied review criteria to every changed file and record a result for each criterion. Use when the user asks for a complete review against requirements, a checklist, or other skills.
---

## Review inputs

- Use the input before this skill's invocation to identify the changes to review and the criteria to apply. Read the supplied criteria, including those from explicitly selected skills and referenced documents. Also read the project guidance that applies to each changed file.
- Identify the exact comparison for the review. State which versions or working changes it includes. If the target or criteria are unclear and cannot be inferred from the input, ask for the missing information.
- List every changed file in that comparison before evaluating the criteria. Include added, modified, renamed, and deleted files.
- List each distinct requirement from the supplied criteria. Preserve individual checks within a section, including conditional checks. Keep each requirement traceable to its source.

## Review each file

- For each changed file, inspect the full diff and enough surrounding code to understand the change. For a deletion, inspect the removed behavior and its consumers. Follow affected interfaces, callers, and tests when they supply evidence for a check.
- Record one result for every requirement and changed file. Use **met**, **unmet**, **not applicable**, **unverified**, or **covered by an approved exception**. Give evidence for met and unmet results, a reason for not applicable and unverified results, and a reference for each approved exception.
- Apply conditional checks wherever their conditions hold. Evaluate checks that span files using the combined evidence and record the result for each affected file. Evaluate each new use against the criteria even if the same pattern exists elsewhere.
- Review and report findings. Leave implementation changes to a separate task.

## Report coverage

- Report each unmet requirement with the affected file, a precise reference, and the impact. Identify checks that remain unverified.
- Include coverage that lets the reader account for every file and requirement. Group results only when the group names every file and requirement it covers and the same rationale applies to each.
- Compare the recorded results with the file list and requirements before reporting. If any result is missing, complete the check or report that the review is incomplete. Report coverage separately from compliance. Claim full compliance only when every applicable result is met or covered by an approved exception.
