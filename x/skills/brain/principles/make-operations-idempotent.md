# Make Operations Idempotent

An idempotent operation gives the same result when it runs once or many times.

Design each operation so it reaches the correct state, no matter how many times it runs or where the last run stopped. Each operation that changes state must answer two questions: "What happens if this runs twice?" and "What happens if the last run crashed halfway?"

Commands, lifecycle steps, and processing loops run where crashes, restarts, and retries are normal. If a partial change from one run changes the result of the next run, each restart becomes a debugging session.

- Base each step on the state that exists, not on what the last run meant to do. Read the current state, compare it with the goal, and apply only the difference. A repeat of such a step finds nothing to do.
- Make each leftover recognizable as stale. A lock, a temporary file, a half-written record, or a claimed job must be something the next run can identify as stale. The evidence must be true wherever the last run stopped, not only in the common case. For example, write to a temporary path and then rename the file into place, or compare files by content and not by creation time.

## Test

1. What happens if this runs twice in a row?
2. What happens if the last run crashed at each possible point?
3. Does running it again always reach the same end state?

If an answer is "it depends on what the last run left behind", add a step that compares the current state with the goal and fixes the difference.
