# Feature

You own the design. Plan, review, and verify. Delegate the implementation. Stay in the lead.

1. Trace the affected subsystem.
2. Run the **architect** skill to choose the shape.
3. Decide how to split the work. Work on code that belongs together, such as one feature or one migration, goes to one owner. That owner can split it further after the blocking steps. Split at your own level only for independent outputs, such as audits or competing experiments.
   - If one worker is enough, write one todo item: `one worker: <reason>`.
   - If the work splits into two or more workstreams, write these four todo items:
     - **Blocking first steps.** The steps that must finish before the work splits.
     - **Independent workstreams.** Separate files, services, or layers run in parallel. Writes to the same target run one after another.
     - **Shared mutable state.** Split the target first, according to the separate-before-serializing-shared-state principle. Serialize only to protect a real invariant.
     - **Smallest safe split.** The fewest workstreams that are safe.
   - Write the split again at each phase boundary.
4. Delegate the code according to the delegation reference. This is required, even for a small change: the agent that writes the code is not the agent that reviews it. A subagent that cannot spawn agents writes the diff itself and keeps the same review separation.
   - Before the delegate writes logic, choose the data shape and its organizing structure according to the model-the-domain principle: a state machine over scattered booleans, a table over branching, a typed model over repeated checks of the same shape. Put them in the brief with the file paths and the success criteria.
   - When the implementation has several valid shapes, such as different error handling, abstraction layers, or test structure, delegate with the **arena** skill.
   - Make small, focused edits. Check a file that is derived from an upstream source against that source again.
   - When you improve a shared part, apply the change in every place that uses it, and verify each one.
   - Commit often.
5. Verify each success criterion where the change runs, with the **verify** skill. A check on the wrong surface, or a result that shows nothing either way, is not a pass. Report it as a gap.
6. Rebase into small, ordered commits, according to the sequence-verifiable-units principle. Build, verify, and commit each unit before the next. Put follow-up work in a stacked pull request.
7. If the design is contested, run the **interrogate** skill before you ship. A design is contested when someone pushed back, the design sketches disagreed, or you chose between close options.
8. Run the **Opening a PR** playbook.

**Reply:** what you built, each choice and why, how you split the work, and the open decisions. Use a table to compare design options.
