---
name: clean-code
description: Check the diff before each commit and remove code that a careful engineer would not write, such as comments that are not necessary, impossible defensive checks, type-checker escapes, and code that does not match the file's style.
---

# Clean code

Read the diff that you are about to commit, or the files that the caller names. Change only lines in that diff. Fix what you find. Do not only report it.

## Remove

- **Comments that the code can say.** Narration of the next line, banners, commented-out code, and notes about the change itself, such as "added", "now uses", or "fix for". If a comment explains a surprise in our own code, remove the surprise: rename, extract a function, or change a type. Then delete the comment.
- **Defensive code that cannot trigger.** A null check, a try/catch, or a fallback for a value that the types or a validated caller already guarantee, according to the boundary-discipline principle. Keep guards at real boundaries.
- **Type-checker escapes.** `any`, `as` casts, non-null `!`, `@ts-ignore`, `@ts-expect-error`, and lint suppressions. Fix the type or the code. Keep a suppression only when its rule is style-only or wrong for this line.
- **Style that does not match the file.** Naming, error handling, imports, and structure that differ from the code around them. Copy the file's pattern.
- **Leftovers.** Debug logs, unused code, unused parameters, and dead branches that the change created.

## Keep

- License headers.
- A comment about behavior that something we cannot change forces: a dependency, a platform, a vendor, or a protocol. Link the issue when there is one.
- Doc comments that state the contract of a public API.
- Formatter directives, such as `prettier-ignore`.

When you are not sure that a keep applies, delete the comment. Before you delete a comment that says "do not remove" or "important", check its claim in the code, or with the **why** skill.

## Report

One to three sentences: what you removed, and what you could not fix inside the diff.
