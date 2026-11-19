# Prove It Works

Before you say that a task is done, check the real thing directly: run the feature, read the actual value, and look at the diff. Proxies do not count, such as file timestamps, a subagent that reports "done", cached output, or "it compiles". When a check fails, first suspect the way that you checked. Then suspect the system.

Script the check when you can. A script that runs the same comparison again is better than one look. Keep its output where the user can see it. Commit it only when the record must be auditable later.
