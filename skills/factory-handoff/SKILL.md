---
name: factory-handoff
description: Save task-relevant thread context as a Markdown handoff for another agent. Use when handing off, checkpointing, transferring, or resuming work between agent turns.
---

# Factory Handoff

1. Resolve the Git project name and branch. Use the workspace name and
   `no-branch` when unavailable.
2. Choose a short kebab-case handoff name unless the user supplies one.
3. Write all task-relevant thread context to:
   `~/.agents-workspace/<project_name>/<branch_name>/<handoff_name>.md`
4. Include the goal, completed work, current state, decisions, constraints,
   changed files, validation, remaining work, blockers, and next step. Omit
   empty sections and unverified claims.
5. Do not overwrite an existing handoff; append a timestamp.
6. Return the saved path.
