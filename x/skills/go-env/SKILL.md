---
name: go-env
description: Choose where a task runs (local, VPS, or cloud) and create it there with x-env. Run it on the local machine from ~/work/<project>. Use for /x:go-env.
disable-model-invocation: true
---

# Go env

Choose where the task runs. If the user names an environment, use it.

- **local**: the user wants to see or use the UI live.
- **vps**: backend work, or a UI change that a screenshot or command output can prove.
- **cloud**: no interaction and no watching needed, and the task is simple.

State the choice and the reason in one line. Then create the task with the **x-env** skill, and start the chief in that task. The chief is the lead agent that runs `/x:go` with the task text:

- **local** and **vps**: in a new Rex tab on that machine.
- **cloud**: as a cloud agent whose prompt starts with `/x:go`.

End with where the chief runs: the machine and the tab name, or the cloud agent's URL.
