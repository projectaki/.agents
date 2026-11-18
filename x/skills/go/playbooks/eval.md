# Eval

You own the experiment design. Plan, blind, run, and synthesize.

**Rules for blinding:**

- Do not use `eval`, `test`, `judge`, `experiment`, `rubric`, `score`, `compare`, `benchmark`, `candidate`, or `arena` in any folder, file, or prompt that a candidate sees.
- The candidate prompt reads like a request from a real user. State the goal, not the experiment.
- Do not ask a candidate to list the skills, principles, or files that it applied. Ask for design notes in general. Grade how it followed the skills from the shape of its code, not from what it says.
- Use folder and file names that a user might choose for a real project.
- Do not tell a candidate that other candidates exist.
- The judge can know that it judges. It sees the outputs only by neutral labels, never by model name.
- To compare two variants, one judge scores both sets in a single pass on one scale, without knowing which set each output came from.

**Steps:**

1. **Frame.** State the variant that you test and the behavior that counts as success. Write the rubric, 3 to 6 concrete criteria, for the judge only. Do not show it to the candidates.
2. **Set up clean folders.** Make one working folder for each candidate, with the variant in place. Add the context that a real task would have, such as a project skeleton.
3. **Write one prompt** that a user would type. It does not show what you measure.
4. **Start the candidates in parallel.** Run each candidate as a headless run in its own folder, with the variant loaded, as the capabilities reference defines it. Choose the runners as in Phase A of the **arena** skill. Give each the same prompt.
5. **Start one blinded judge** on a model from a different family, as in Phase C of the **arena** skill. The judge sees the outputs by neutral labels and the rubric, never a model name.
6. **Check what each candidate did from its session transcript, not from its report.** See which files it really opened. Grade how it followed the skills from the files that it read and the shape of its code, never from its own claims.
7. **Read every candidate output yourself**, from start to end. Compare your reading with the judge's verdict. A disagreement means that a model is biased or that the rubric is unclear. Combine the results.

**Reply:** the variant that you tested, the rubric, notes for each candidate, the judge's verdict, your combined result, and whether to promote the variant.
