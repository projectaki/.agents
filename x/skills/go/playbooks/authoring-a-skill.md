# Authoring a skill

You own the skill's voice.

1. Write the skill with the **clean-text** skill. Keep only text that changes a decision. Tell the agent what to do, and give the reason only when the rule is confusing without it. Point to other skills and principles by name. Do not repeat their rules. Point to structural sources, such as types, READMEs, or config, according to the encode-lessons-in-structure principle.
2. Put each piece where it belongs: a rule about the code goes in a **brain** principle, and a rule about how the agent works goes in **go**, as a trigger, a reference, or a playbook. A harness's tools, models, and flags go only in its adapter skill. Everywhere else, use the words in the capabilities reference. Add every new principle, reference, or playbook to its index.
3. Validate: the frontmatter has `name` and `description`, every referenced file exists, every link to another skill resolves, and the plugin validates.
4. If the skill changes structure or flow, test it on a sample task. Skip this for a change in wording only.
5. Run the **Opening a PR** playbook.

When in doubt, delete. If you keep hitting a workflow that no skill covers, propose a new skill.

**Reply:** a summary of the skill, the key design decisions, and the validation results.
