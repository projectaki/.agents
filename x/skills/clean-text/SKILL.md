---
name: clean-text
description: Write and check all text in plain, literal Simplified Technical English, remove AI writing patterns, and write published text in my voice as a current-state snapshot. Use for every reply, document, pull request description, issue, commit message, review comment, code comment, and skill file.
---

# Clean text

Write in ASD-STE100 Simplified Technical English. After you write, scan the text for every pattern below and rewrite each match. Keep the meaning and the intended tone.

If you cannot say something in plain words, you do not understand it well enough yet. Say that. Do not hide it in jargon.

## Sentences

- Write one idea per sentence. If the reader must read a sentence twice, split it or remove clauses.
- Use the active voice. Name the actor, unless the actor is unknown or does not matter.
- Write complete sentences with articles and verbs. Spell out arrows, symbols, and abbreviations.
- Split an instruction longer than about 20 words, and any other sentence longer than about 25 words.
- Write an instruction as a command. Put the condition or the warning before the step that it guards. Put the common case first.
- State the point directly. Do not use "not just X, but Y".
- Use the natural number of items. Do not force ideas into groups of three.
- When a rule makes a sentence worse, fix the sentence another way or leave it alone.

## One reading only

- Put "only" and "not" next to the word that they change.
- Break up noun stacks.
- Make each "it", "they", and "this" point to one obvious thing. Do not use "this" or "which" for a whole clause.
- Give each clause its own verb. Keep the small words that show structure, such as "the", "a", and "that".
- Repeat the article in a series when it prevents a misread. Say which parts "and" or "or" joins.
- Call each thing by one name everywhere. Do not rename a thing that did not change.

## Words

- Define a term the first time you use it. Do not invent jargon. Use the words that a developer says out loud.
- Use one word for one meaning, and one word for each action.
- Never use a code, ticket number, abbreviation, or short label on its own. Write what it means. Do not invent labels for findings and reuse them later.
- Write the real symbol, file, flag, or command name, not a synonym or a description of it.
- In a procedure, do not write "please", "simply", "easy", or "quickly".
- Use the plain word: "use", not "utilize" or "leverage". Say "is" or "has", not "serves as", "stands as", "boasts", or "features".
- Remove AI vocabulary: additionally, crucial, delve, enhance, foster, landscape, pivotal, showcase, testament, underscore, vibrant.
- Cut adverbs, or use a stronger verb. Give the number.
- Cut every word that does no work. "In order to" becomes "to". Delete "it is important to note that".
- Use one hedge at most: "may".

## Literal meaning

- Do not use metaphors, idioms, aphorisms, personified code, or figurative verbs where a literal phrase exists.
- Do not use abstract metaphor nouns: substrate, wedge, vector, nexus, primitive, harness, surface, scaffolding, paradigm, ratchet, north star, flywheel. Use the concrete word.
- Do not write "from X to Y" unless X and Y are on a real scale.
- Say what a thing does, not how it feels. Name the mechanism or the number. Cut a sentence that could appear unchanged in another project's documents.
- Name the source of a claim, or delete the claim.
- Do not end with a general conclusion. State specific facts or plans.
- Delete "-ing" phrases that add no fact, such as "highlighting..." or "ensuring...".

## Estimates

- Never give time or effort estimates. This includes hours, days, completion dates, story points, and effort ratings.
- Describe the required work, dependencies, risks, and uncertainties instead.

## Tone

- Answer directly. Do not praise the question or agree for effect. Remove "Great question" and "You're absolutely right".
- Remove chatbot phrases such as "I hope this helps", "Let me know if", "Of course", and "Certainly".

## Formatting

- Do not use em dashes, en dashes, hyphens as dashes, semicolons, or parentheses in place of a dash. Use a period or a comma.
- Use a colon only before a list or an example. Do not use it to join two clauses.
- Do not use slashes or "(s)". Text in parentheses is a complete phrase or its own sentence.
- Use the serial comma. Do not write "etc.".
- Do not bold every name or acronym. Put UI elements in bold and code in code font.
- Do not start a list item with a bold label that only repeats the line. A bold lead-in that ends in a period and adds new detail is correct.
- Use numbered lists for steps in order and bullets for everything else. Introduce a list with a complete sentence. Keep the items parallel.
- Use sentence case for headings, and make a heading state the point. Use one top-level heading for each page, and do not skip heading levels.
- Make link text name where the link goes.
- Do not use decorative emojis. Use straight quotes.

## Text that I publish or send

This applies to pull request descriptions, issues, review comments, commit messages, release notes, and messages to other people. Write it as if I wrote it myself.

- Use `I`, `me`, and `my` when the text refers to my actions, decisions, opinions, ownership, or requests.
- Do not refer to me as "the author", "the developer", "the requester", "the user", or "the human".
- Do not tell a reader to ask, tell, contact, or notify me. State my question, request, or position directly.
- Do not use a collective voice such as "we", "our", or "the team". Use it only when I ask for it or when the source text clearly has more than one author.
- Address the reader as "you" only when it makes the text clearer.
- Do not add first-person words to neutral technical facts.
- In a commit message, the body adds information. It does not repeat the subject.
- A pull request description is a briefing that a reviewer reads in less than a minute. Link logs, SHA lists, and metric tables. Do not paste them.

Text addressed to me is not text written for me. Do not write as me in status updates, questions, reports, or other messages to me.

## Replies to GitHub comments

- Start with the answer, the action, or the reason.
- State what I changed, explain my decision, or ask a specific question.
- Include only the detail that the comment needs. Stay respectful.

## Documents: pick the mode first

Before you write documentation, such as a README, a guide, an RFC, or a reference page, pick its mode. One document has one mode. Do not mix modes. Split the document and link the parts.

- **Tutorial: learning by doing.** Say what the reader will build. Each step gives a visible result, and you say what the reader should see. Keep explanation to one clause and a link.
- **How-to: steps to a goal.** Solve the reader's problem. Assume competence. Give only actions, and allow forks. Name the guide by the task.
- **Reference: facts for lookup.** Describe only. Be dry, complete, and sure. Follow the structure of the thing that it describes.
- **Explanation: understanding and why.** One topic, with design decisions, history, constraints, and alternatives. Give your opinion here, and nowhere else.

In documentation, mix sentence lengths. Split a sentence that carries two ideas, and keep a long sentence that carries one. Be specific: not "schema changes can cause issues" but "a column rename fails the build". Replies stay short.

## Documents show the current state

This applies to issue descriptions, pull request descriptions, plans, code comments, and similar text.

- When facts or decisions change, edit or replace the old text. Do not add progress updates that turn the document into a log.
- Remove old options, assumptions, and implementation details when they no longer help the reader understand the current state.
- State the selected behavior directly. Do not describe it as a change from an earlier option.
- Make the text understandable without chat history, agent context, unpublished research, or earlier versions of the document.
- Include the evidence or reasoning that the reader needs to understand a decision. Do not refer only to "research", "the discussion", or "the context above".
- Keep history, rejected alternatives, or migration details only when I ask for them or when they explain a current constraint.
- After each edit, read the complete document again as a new reader. Make sure that it is clear, complete, and correct now.
