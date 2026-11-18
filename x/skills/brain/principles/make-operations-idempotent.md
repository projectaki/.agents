# Make Operations Idempotent

Design each operation that changes state so it reaches the correct state, no matter how many times it runs or where the last run stopped.

Base each step on the state that exists, not on what the last run meant to do. Read the current state, compare it with the goal, and apply only the difference.

The next run must be able to identify each leftover as stale, such as a lock, a temporary file, a half-written record, or a claimed job. The evidence must be true wherever the last run stopped. For example, write to a temporary path and then rename the file into place.

Test: what happens if this runs twice? What happens if the last run crashed at each possible point? If the answer depends on what the last run left behind, add a step that compares the current state with the goal and fixes the difference.
