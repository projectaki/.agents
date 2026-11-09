---
name: x-bug-fix
description: Fix an already identified bug with regression tests and save before-and-after evidence, including screenshots or video for behavior visible on the affected platform.
---

Inputs: Identified bug, expected behavior, and relevant code.

- Start with an identified bug and its expected behavior.
- Write the simplest regression tests that reproduce it: unit, integration, or end-to-end tests, as appropriate.
- Run the tests before changing the code. Confirm they fail because of the bug and save the test output.
- If the bug is visible on the affected platform, reproduce it through the normal user flow before changing the code. Save a screenshot that shows the failure, or a video if reviewers need to see the interaction or sequence.
- Make the smallest code fix that addresses the bug.
- Rerun the same tests without weakening their assertions. Save the passing test output.
- For bugs visible on the platform, repeat the same user flow with equivalent inputs and setup. Save a matching screenshot or video that shows the expected behavior. Keep the before and after files separate and label them clearly.
- Keep the regression tests. Include links to the saved before-and-after evidence in the handoff or review summary. Use a shared artifact location when available and authorized so reviewers can open the files. If reproduction, verification, or visual capture is blocked, state which evidence is missing and why.
- When fx supplies a handoff file, keep it current with scope and success criteria, original approval references and limits, exact source identity, required test setup, completed checks, and remaining findings. Include paths to the before-and-after test output and visual evidence. Distinguish observed results from planned checks. Do not treat an agent summary as approval.
