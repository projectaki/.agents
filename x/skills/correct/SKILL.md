---
name: correct
description: Find the mistakes that agents keep repeating in this repo and make each one impossible. Try architecture first, then types, then a lint whose error names the fix, then a test, and write docs last. Prove that each check fails on a real past mistake. Use when I correct the same mistake again.
---

# Correct

I keep correcting agents in this repo for the same mistakes. Change the repo so that the next agent cannot make them. This is the encode-lessons-in-structure principle, applied to a whole repo.

Assume that every contributor is an agent that sees only the files it opened, copies the nearest example, and takes the shortest path that compiles. Design the repo so that a change that looks right in one file is right for the whole repo.

## Find the mistake classes

First, read the recent commits, reverts, review comments, agent instruction files, and comments that explain workarounds. Group the mistakes into classes. A class counts once it has happened twice.

## Fix each class at the highest level that works

1. **Remove it with architecture.** Give each piece of state one owner, and each task one supported way. Hide internals so that the wrong import fails. Replace lists that are kept in sync by hand with one source of truth. Delete old ways and dead code that an agent would copy.
2. **Enforce it with types,** so that the bad state cannot be written. If bad code still compiles, add a lint or a CI check whose error names the file, type, or function to use instead. If the pattern is already common, fail only when a change adds more of it.
3. **Test the behavior.** Fix or delete each test that still passes when the behavior it checks breaks, or that fails when only the internals change.
4. **Write docs or agent rules last, and only for judgment calls.** Nothing fails when an agent skips them.

## Fix and prove

Then fix the most frequent classes now, with one commit for each. Prove that each new check fails on a real past mistake. Run the same command locally and in CI. An exception goes on the line that breaks the rule, with a reason, an expiry date, and my approval.

## Keep the rule table

Last, keep a table in the repo's agent instruction file that pairs each rule with what enforces it. When I correct you, fix the mistake and add the rule. If the rule was already there and nothing enforces it, that is a repeat, so fix it at the highest level in the same change. Remove a rule when its mistake can no longer happen.

**Reply:** each class with its evidence, the level that you chose, and why a higher level did not work.
