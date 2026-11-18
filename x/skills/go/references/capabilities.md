# Capabilities

Core skills name what they need with the words below. They never name a harness's tools, models, or flags. The adapter skill for your harness says how to get each capability. If your harness cannot provide one, use the adapter's fallback and say so in one line.

- **Background subagent**: an agent that runs in parallel with you and returns one result.
- **Fresh subagent**: a background subagent that sees only its brief, not your conversation. Every subagent is fresh unless a skill says otherwise.
- **Read-only subagent**: a background subagent that does not edit files. After it finishes, check `git status`.
- **Worktree subagent**: a background subagent that works in its own git worktree.
- **x-agent**: the delegate defined in `agents/x-agent.md` in the x plugin.
- **Strongest model, second model, fast model**: the models of your own vendor. The second model is from a different model family than the strongest.
- **Other-vendor model**: a model from a different company than the one whose model runs you.
- **Effort**: how much a model thinks before it answers.
- **Todo list**: a visible list of steps that you update as you work.
- **Ask the user**: a question to the user, with options when the choices are known.
- **Run a skill**: load another skill's instructions and follow them.
- **Validate the plugin**: check the x plugin's manifest and skills.
