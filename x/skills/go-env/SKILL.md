---
name: go-env
description: Choose where a task runs (local or VPS) and create it there with x-env. Run it on the local machine. Use for /x:go-env.
disable-model-invocation: true
---

# Go env

Choose where the task runs. If the user names an environment, use it.

- **local**: the user wants to see or use the UI live.
- **vps**: backend work, or a UI change that a screenshot or command output can prove.
- **cloud**: not built yet. When a task fits it (no interaction, no watching, and simple), use **vps** and say that cloud would fit.

State the choice and the reason in one line. Then follow the **x-env** skill:

1. Install x-env on this machine.
2. Find the project: the current folder inside `~/work/<project>`, or the project that the user names. On **vps**, add `--host vps --project <project>` to each command after setup, because the VPS cannot see your current folder. `vps` is the label of the VPS in `rex hosts`. If the user names another host, use that label. If no host has the label, stop and ask the user for it.
3. Run `x-env setup <project> <repository>` if the project does not exist on that machine yet.
4. Create the task with `x-env task <name>`. Choose a short name in kebab case from the task text.
5. Start the chief with `x-env chief --task <name> --prompt "<task text>"`. The chief is the lead agent. It runs `/x:go` with the task text in a new Rex tab on that machine.

End with the machine, the task name, and the Rex tab label that the chief command printed.
