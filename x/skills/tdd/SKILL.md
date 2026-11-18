---
name: tdd
description: Fix a bug test-first. Write a focused test that fails before the fix and passes after it. Use when the user asks for a failing or regression test, or when the bug has a cheap local test.
---

# TDD

When a bug has a clear and cheap test path, make the broken behavior executable before you change production code. The goal is a focused regression test that fails before the fix and passes after it.

Do not force a test that is impractical. If the test would need a broad harness setup, brittle mocks, slow end-to-end infrastructure, production-only state, vague reproduction steps, or a lot of unrelated fixture changes, do not add a new test. Use the closest useful check instead.

## Steps

1. **Understand the bug.** Find the intended behavior, the current behavior, the affected path, and the smallest reproduction that you can observe.
2. **Choose the narrowest check that you can run.** Prefer the closest unit, component, integration, or regression test that this code path already uses. If no practical test path is clear, do not build one from nothing only to follow these steps.
3. **Write the failing test first.** Add the smallest focused test that would have caught the bug. It tests the intended behavior, according to the testing principle.
4. **Run the new test before the fix.** Confirm that it fails for the intended reason. If it passes, or fails for another reason, correct the test or the reproduction before you change the code.
5. **Fix the bug.** Make the smallest production change that gives the intended behavior and keeps the nearby contracts.
6. **Run the test again.** Confirm that it passes.

## When a failing test is impractical

Use the closest regression check that you can run: a targeted script, a reproduction command, browser automation, a snapshot comparison, a log assertion, or a focused integration check.

Prefer no new test over a bad test. A bad test mostly tests mocks, encodes implementation details, depends on timing or unrelated global state, needs expensive infrastructure for a small fix, or would be deleted right after it proves the fix.

## Rules

- Do not change a test only to match a wrong implementation.
- Do not weaken an existing assertion unless the expected behavior really changed and the reason is clear.
- Keep the test on the bug. Do not add broad fixture changes or unrelated coverage.
- If the bug is flaky, make the test deterministic where possible, and say which signal it locks down.
- If the bug shows a wider class of failures, land the focused test first. Then consider tests for the related cases.

## Report

Report the evidence, not only the outcome:

- The test or check that failed before the fix, and its failure.
- The run that passed after the fix, and any nearby checks.
- If you could not show a failure before the fix, say why, and name the closest check that you used.
