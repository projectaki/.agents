# Bug fix

You own this task. Plan, review, and verify. Delegate the investigation and the fix. Stay in the lead.

Every line that you ship traces to runtime evidence. A change that "might help" is a hypothesis, not a fix, and it does not ship. When evidence disproves a hypothesis, revert the changes that it caused. Ship the smallest change that the evidence supports.

1. Reproduce the bug yourself where it happens, with the **verify** skill. If it does not reproduce, create the trigger, narrow the conditions, or add logging until it does. Ask the user only when you cannot reach that surface, and state the specific reason.
2. Find the cause by elimination. List the candidate causes from a trace of the affected code and from its history with the **why** skill. In each round, run the check that rules out the most candidates. When the program state is unclear, add logging and read it while the code runs. Do not guess. Confirm the cause with runtime evidence before step 3.
3. Plan the fix according to the fix-root-causes principle. Delegate it according to the delegation reference.
4. Verify on the same surface: the reproduction from step 1 now passes. A check on the wrong surface, or a result that shows nothing either way, is not a pass. A unit test shows how a branch behaves. It does not show that the bug is gone.
5. Order the commits so that the failing reproduction lands before the fix, according to the sequence-verifiable-units principle. When the bug has a cheap local test, follow the **tdd** skill. Skip this when a test would be expensive or unclear.
6. Run the **Opening a PR** playbook.

**Reply:** what was broken, the root cause, the fix, and how you verified it. Paste the failing and then the passing reproduction output, word for word.
