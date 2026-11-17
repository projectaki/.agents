# Build the Lever

When the work is not trivial, build a tool that does the work. Do not do it by hand.

A codemod, a generator, or a script does the work the same way every time, and you can run it again at no cost. A reviewer can read and run the tool to check the work. A change made by hand can only be checked by doing it again. A script turns "trust me" into "run this".

Build the tool by default. Skip it only when the task is trivial: a few obvious edits that you can see at a glance. The limit is triviality, not repetition. A one-time task still needs a tool when the tool is what makes the work possible to check.

- Do the first unit by hand to learn the steps. Then build the tool. Prove the tool: run it on that unit and compare its result with your manual change. Make the tool safe to run again.
- Use a codemod or a script for edits, a generator for repeated files, a query for analysis, and a check that you can run again for verification.
- A tool is better than many subagents. If one script can process every unit in one pass, run it yourself. Do not send subagents to apply by hand what a script can do.
- When you give work to subagents, write the steps, the check, and the files they must not change in one skill file that they all read. Keep that file outside the files that they can change.
- Build the smallest script that does or proves the job. Never build a framework.
- Commit the tool when the work continues after the session.

When you apply this principle, the result is a file. If you name this principle and the diff has no script, codemod, generator, or subagent skill, you did not apply it.
