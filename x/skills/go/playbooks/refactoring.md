# Refactoring

You own the contract. The structure changes. The behavior does not. Feature adds behavior, and Bug fix corrects it.

If the cleanup reveals a missing feature or a real bug, split it out, and ship the structural change first against the pinned behavior. A redesign is allowed, but name it and use the Feature playbook.

1. Pin the behavior first. Trace the affected code to learn its contract. Then write a characterization test, a snapshot, or an equivalence check that captures the current behavior before any structure moves. A type check or a lint is not a pin.
2. Name the structure that the code is missing, according to the model-the-domain principle. Keep simple code when its shape is already clear and local. The new shape must remove branches or invalid states, not add indirection.
3. Name the target shape: the module layout, the types, and the call graph if you built it today, according to the foundational-thinking and redesign-from-first-principles principles. If the target crosses a function boundary, run the **architect** skill first.
4. Remove before you add, according to the subtract-before-you-add principle. Revert a speculative cleanup that "might help".
5. Move in small steps that keep the pin green. For an API change, replace every caller and delete the old API in the same change, according to the outcome-oriented-execution principle. Check each rename against the actual files, because renames miss uses in strings, text, and references. Delegate the mechanical edits according to the delegation reference.
6. Prove that the behavior did not change on the real result, according to the prove-it-works principle. "It compiles" is not proof. For a larger change, run an equivalence check: a script that compares old and new outputs, a recorded baseline replayed against the new code, or a run with the **verify** skill.
7. Keep the change only if it lowers reader load somewhere, according to the readability principle. Otherwise, revert it.
8. Rebase into small, ordered commits: the removal first, then the new shape, then any follow-up cleanup, according to the sequence-verifiable-units principle. Run the **Opening a PR** playbook.

**Reply:** the structure that changed, the pin you held it against, the proof that behavior is equal, how reader load changed, and what shipped and what you reverted. No new behavior.
