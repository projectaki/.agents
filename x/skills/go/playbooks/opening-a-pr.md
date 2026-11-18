# Opening a PR

Run at the end of every other playbook.

1. Work from a git worktree off `main`, and keep unrelated work out of it. Rebase into small commits that can each land. Check the diff with the **clean-code** skill. Write the title, the description, and each commit message with the **clean-text** skill.
2. Write the title as `type(scope): subject`. Name a real symbol when one carries the change.
3. Write the description as a one-minute briefing for a reviewer who has the diff. Keep it under about 40 lines. Use these `##` sections in this order, and leave out a section that has nothing to say:
   - `## Why`: the problem and the approach, in 1 to 3 sentences.
   - `## What changed`: 1 to 3 bullets. Name a symbol or path only when it carries the change.
   - `## Scope`: always. What the change covers, and what it leaves out on purpose.
   - `## Tradeoffs`: only alternatives that a reviewer would ask about.
   - `## Blast radius`: who or what the change touches, and why that is safe or risky.
   - `## Verification`: 1 to 3 bullets, each a real check and its result.

   Add screenshots or videos after the sections when they prove a claim.
4. For a stacked pull request, set the base to the parent branch: `gh pr create --base <parent-branch>`. Branch from `main` only for independent work.
5. Open the pull request as ready, not as a draft. Run `gh pr view <number>` before you state its status.
6. Post the URL and continue. A subagent that opens a pull request returns the URL to its parent.
