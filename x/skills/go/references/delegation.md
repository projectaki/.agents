# Delegation

There are two kinds of delegation. Use a background subagent unless the work needs a visible session.

## Background subagent

A background subagent, as the capabilities reference defines it.

Use it for all delegated work that does not need a visible session. Examples: explore code, sketch a design, implement a scoped change, run a check, review a diff.

### Model and effort

Use the current session's model by default. Raise the effort for the hardest work, such as a design that touches many parts or subtle concurrency. Lower it for mechanical edits and checks.

### Fresh subagents

Give each new round of work, such as a fix after review, a follow-up, or a retry, to a new subagent. Its brief contains the original brief, every later instruction, and the earlier agent's report and changes. Send more work to an existing subagent only when the work needs state that lives in that agent and is hard to move: uncommitted changes, its own checkout, or a process that it runs, such as a dev server.

### Other-vendor model

When the work needs a model from another vendor, run it as a background shell command that writes its output to a file, as the adapter skill of that vendor says. Read only the end of the file. Never call your own vendor's CLI. For your own vendor's models, use a background subagent.

## Visible session

A new x-env session in a new Rex tab. The user can watch it, steer it, and talk to it.

Use it only when:
- the user may need to see, steer, or answer the agent
- the user may want to resume the session later
- the user asks for one

Without Rex, such as on a cloud agent, there are no visible sessions. Use a background subagent and say so in your reply.

## Rules for both

- You own each agent's work. Review the diff and check the result yourself. Write your own summary from what you checked. Do not pass on the agent's report.
- For a second opinion, send the same prompt to another vendor's model.
- One agent edits a worktree at a time. An agent that edits in parallel needs its own worktree.
- Give each agent the goal, the scope, the files, the success criteria, and what to return.
- Spawn each background subagent as an x-agent. Give it the absolute path to the x skills folder.
