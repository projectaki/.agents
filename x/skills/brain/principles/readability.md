# Readability

Prefer:

- guard clauses
- early returns
- shallow control flow
- explicit behavior
- self explaining code without code comments

Avoid deep nesting whenever possible.

## Code Comments

Treat a code comment as a last resort. Add one only when critical information
must remain beside the code and cannot be made clear through naming, structure,
types, or tests.

- Keep comments short. Do not write large paragraphs or detailed narratives.
- Explain a necessary constraint, workaround, or non-obvious reason. Do not
  restate what the code does.
- Put broad reasoning, implementation history, and review context in the pull
  request description or durable documentation instead.
- Do not add a comment only because information was useful during development.
- Remove a comment when the code no longer needs it or when the information is
  no longer accurate.
- Before adding a comment, first try to make the code self-explanatory.
