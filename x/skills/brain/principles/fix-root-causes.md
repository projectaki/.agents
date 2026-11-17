# Fix Root Causes

When you debug, fix the fault, not the place where it appeared. The symptom is where a wrong state became visible. The root cause is the first place where the system did something that it must not do, or did not handle a state that it must handle.

A fix at the symptom hides the evidence and lets the fault appear somewhere else. Each such fix makes the system harder to understand, because the code now contains a workaround for a bug that nobody named.

- Reproduce the bug first.
- Ask "why" at each step until the answer is a wrong decision in the code, not a result of an earlier decision.
- When you are stuck, add instrumentation. Read the actual error and the actual state. Do not guess.
- Ask whether the state that caused the symptom is valid. If the system is allowed to be in that state, the code that failed on it is the root cause, and handling the state there is the fix. If the state must never exist, a check where it failed hides the bug. Find what created the state. Guards, retries, swallowed errors, clamped values, and discarded state are the common ways to hide a bug.
- When something fails only after a restart, suspect stored state first: config files, caches, lock files, and saved state.
- Fix the pattern, not only the instance. Find every place that has the same fault and fix them all.
- If a workaround needs a long comment to justify it, the code is wrong. Fix the code, not the comment.
- If the deciding fact took a deep search to find, propose a cheap signal that shows it at once, such as a log line or a metric.
