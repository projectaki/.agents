---
name: bug-fix
description: Fix an already identified bug with regression tests and recorded evidence of failure before the fix and success after it.
---

- Start with an identified bug and its expected behavior.
- Write the simplest regression tests that reproduce it: unit, integration, or end-to-end tests, as appropriate.
- Run the tests before changing the code. Confirm they fail because of the bug and record the evidence. Prefer test output; use screenshots or video when needed to show the behavior.
- Make the smallest code fix that addresses the bug.
- Rerun the same tests without weakening their assertions. Record passing results and any matching visual evidence needed to show the fix.
- Keep the regression tests. Report the before-and-after evidence. If reproduction or verification is blocked, state what is missing instead of claiming success.
