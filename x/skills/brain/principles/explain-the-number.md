# Explain the Number

Before you measure, and before you trust, report, or act on a number that you measured, find what limits it. Rule out that it measures something other than the work you think. Examples are a speedup, a regression, a throughput, a latency, and an eval result.

- **Write the decision before you run.** Name the result that would change a decision, and the noise floor. Stop when the spread between runs is larger than the effect.
- **Ask "why not double?"** Name the resource or code path that limits the result, such as a core, a lock, the disk, the network, or the load generator itself. Get it from a profile or from system counters taken during a run, then map it to the source. A guess from reading the code is not a limiter. If you cannot say why the number is not twice as good, you do not know what you measured.
- **List what else the number could measure, and rule out each one with evidence.** The usual causes are errors, skipped or cached work, code that never ran, an untuned side that kept its default settings, noise, and a part too small to matter end to end.
- **Keep the evidence with the number.** Put the run count, the spread, and the limiter in the notes or in a linked file.

For a performance number, run the full procedure with the **benchmark-checklist** skill. For an eval result, ask the same of the trials: did every run do the task, does the gap hold across trials and models, and does the scenario matter.

You skipped this principle when a run started without the result that would change a decision, when a number has no run count, spread, or named limiter, or when the time saved is larger than the time that the changed part took.

This is different from [Prove it works](prove-it-works.md), which checks that an output is real.
