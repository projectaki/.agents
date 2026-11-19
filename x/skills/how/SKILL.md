---
name: how
description: Explain how code works, before a change or for onboarding, and answer where something should live, which package owns it, or which layer is right. Use why for the reasons behind it.
---

# How

Before you start, read the adapter skill for your harness, such as `../adapter-claude-code/SKILL.md` from this file. It maps the capability words in this skill, such as "fresh subagent", to your harness's tools.

Explore the codebase to answer a "how does X work?" question.

If the scope is unclear, state how you read it and start. The user can redirect you.

## 1. Explain

Start one read-only fresh subagent that explores and explains in one pass. Give it the user's question and this brief:

> You are writing an architectural explanation for a senior engineer. Explore the codebase and write an explanation that a senior engineer who does not know this area can read and come away with a solid mental model. They understand the architecture well enough to start working in it with confidence. You can read the codebase, but do not edit it.

## 2. Present

Present the subagent's output. Small edits for clarity or for context from the conversation are fine. Do not rewrite it.
