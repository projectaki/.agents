# Prove It Works

Before you say that a task is done, check the result by looking at the real thing directly. Do not infer that it works from a proxy, from a self-report, or from "it compiles".

Work that nobody checked might be wrong. Indirect checks feel cheaper than direct ones: file timestamps, output that looks recent, a subagent that reports "done", or old screenshots. Acting on a wrong guess costs much more than checking the source.

- Check that a process runs by asking the process itself, not by looking at state derived from it.
- Read the actual value, not a cached or derived copy.
- When a check fails, first suspect the way that you checked. Then suspect the system.
- Script the check when you can, according to [Build the lever](build-the-lever.md). Keep its output so that a reviewer can run it again.
