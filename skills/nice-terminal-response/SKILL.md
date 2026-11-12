---
name: nice-terminal-response
description: Format responses for easy reading in a terminal. Use when the user asks for terminal-friendly replies or when another skill calls for this format.
---

# Format responses for the terminal

Use plain names, short paragraphs, and single-level lists. Use bullets or separate labeled paragraphs for comparisons that need to wrap in narrow panes. Keep tables and nested lists out of decision turns.

Put an actual empty line after a heading, between paragraphs, between individual list items, around a fenced block, and before a final question. A single line break can render as part of the same paragraph. If the terminal renders list items without space between them, use separate paragraphs with short labels instead.

Show file trees in fenced text blocks. Put explanations below the tree so they can wrap. Explain technical names when they matter. Check that every sentence and bullet is complete before sending.

## Present a decision

1. Start with a short heading that names the choice.
2. State your recommendation and main reason in one or two sentences.
3. Show the evidence and tradeoff needed to decide. For a simple choice, use at most three short bullets when a list helps.
4. End with one bold question that the user can answer in one line. Give short answer options when they help.

Example

> **Who should run the tests?**
>
> I recommend a manager so the tests exercise access limits.
>
> - A manager can see only the divisions they have access to.
>
> - An administrator can see the entire organization.
>
> **Should the tests run as the manager?**
