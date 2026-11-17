# Separate Before Serializing Shared State

Before several actors share state, ask: "What happens if another actor changes this at the same time?" If the answer is not "nothing", act on this principle. Actors are processes, threads, subagents, or workers that run at the same time.

First ask whether the actors need the same changeable object. If they do not, remove the sharing. If they do, enforce one-at-a-time access with a mechanism, such as lock files, phases that run in sequence, or a single owner. Instructions and conventions do not control concurrency.

Concurrent writes to shared state cause race conditions. They occur only sometimes, are hard to reproduce, and are expensive to debug.

1. Find the shared state that changes: files that several actors read and write, branches that several actors push to, and APIs that one actor defines while another uses them.
2. By default, remove the shared write target. Ask whether the actors need one shared object, or whether each one only records its own facts. Give each actor its own file, key, branch, or state folder. Combine the results only where they are read or reported. Two workers that each write their own field into one `state.json` still share a file. `indexer-state.json` and `metrics-state.json` share nothing.
3. Only when one shared target is a real requirement, enforce one-at-a-time access with a mechanism: lock files, phases in sequence, a single writer, or an atomic compare-and-swap. Treat "we need a lock" as a reason to check the design again, not as the default answer.
