# Fix Root Causes

Fix the fault, not the place where it appeared. The root cause is the first place where the system did something that it must not do, or did not handle a state that it must handle.

- Reproduce the bug first. Ask "why" until the answer is a wrong decision in the code. When you are stuck, add instrumentation and read the actual state.
- Ask whether the state that caused the symptom is valid. If it is valid, handle it where the code failed. If it must never exist, a check there hides the bug, so find what created the state. Guards, retries, swallowed errors, clamped values, and discarded state are the common ways to hide a bug.
- Fix the pattern, not only the instance. Find every place that has the same fault.
- If the deciding fact took a deep search to find, propose a cheap signal that shows it at once, such as a log line or a metric.
