# Prototype

You own the design decision, not the code. The prototype is a throwaway tool. The real build follows the Feature playbook.

In this playbook, the usual rules for small, clean, and verified code do not apply. Speed matters more than quality, and there is no planning. The care goes into choosing the right design cheaply. Propose variations that the user did not ask for. Throw an approach away and try another.

1. State the decision that the prototype must make: which layout, interaction, or density, or for an open question about behavior, which behavior, timing, or approach. If there is no decision to make, use the Feature playbook instead.
2. When the design space is open, collect references. Search for existing examples, and summarize the themes, palettes, and layouts. Let the user choose directions before you build. Skip this when the direction is set.
3. Build the throwaway in a scratch folder, separate from the production source. For a visual decision, use plain HTML, CSS, and JavaScript, or the lightest stack that shows the idea, with CDN dependencies and a dev server that reloads. For a behavior or timing decision, write the smallest script that tests the question. No production framework, no tests, no abstractions.
4. To compare alternatives, put them behind one switcher, such as buttons or a key press, and label each variant. This applies the exhaust-the-design-space principle cheaply.
5. Check each variant where it runs, with the **verify** skill. For a visual decision, take a screenshot of each variant and use the interaction. For a behavior or timing decision, observe the result: log the timing, print the output, or watch the render. The observation is the test.
6. Present the alternatives, the tradeoffs, and a recommendation. The result is the decision and the throwaway code, not code to ship. Hand the chosen direction to the Feature playbook, or to the **architect** skill for the code shape.

**Reply:** the variants, the evidence (screenshots for a visual decision, the observed output or timing for a behavior decision), the tradeoffs, your recommendation, and the scratch folder path. State that the prototype is throwaway.
