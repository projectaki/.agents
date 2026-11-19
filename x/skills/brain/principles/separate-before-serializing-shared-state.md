# Separate Before Serializing Shared State

When actors that run at the same time can write the same file, branch, key, or object, first ask whether they need one shared object or each only records its own facts. Actors are processes, threads, subagents, or workers. By default, give each actor its own file, key, branch, or state folder, and combine the results only where they are read. Two workers that each write their own field into one `state.json` still share a file.

Only when one shared target is a real requirement, enforce one-at-a-time access with a mechanism, such as a lock file, a single writer, phases that run in sequence, or an atomic compare-and-swap. Instructions do not control concurrency. Treat "we need a lock" as a reason to check the design first.
