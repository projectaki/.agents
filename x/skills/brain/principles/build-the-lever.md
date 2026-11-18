# Build the Lever

When the work is not trivial, build a tool that does the work, such as a codemod, a script, a generator, or a check that you can run again. Do not do it by hand. The limit is triviality, not repetition. Skip the tool only for a few obvious edits.

- Do the first unit by hand. Then build the tool, and prove it: run it on that unit again. Make the tool safe to run again.
- A script is better than many subagents. When you do give work to subagents, write the steps, the check, and the files they must not change in one skill file that they all read and cannot change.
- When you apply this principle, the result is a file. If the diff has no script, codemod, generator, or subagent skill, you did not apply it. Commit the tool when the work continues after the session.
- Build the smallest script that does or proves the job. Never build a framework.
