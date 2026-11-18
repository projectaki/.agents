---
name: blast-radius
description: Find what a change could break outside the diff before it ships, and prove the one fact that makes it safe by running real code. Use for "blast radius of X", "what could this break", or a small diff that I do not trust.
---

# Blast radius

Find what a change breaks somewhere else, before it ships.

This is the companion of the **how** and **why** skills. **how** says what the code does. **why** says why it has that shape. Blast radius says what it breaks somewhere else.

A list of callers is not the job. A search finds those in a second. The job is the breakage that a search does not show.

## Do not trust your own write-up

A blast-radius write-up that sounds right is worthless, because it sounds convincing whether or not it is true. So do not hand back only a write-up. Find the one or two facts that the whole change depends on, and prove them by running code.

### How sure you are

For each fact that the change's safety depends on, get it as far down this list as is cheap, and say where it stopped.

1. You said so. This is worthless on its own.
2. You pointed at the line: a real `file:line`, or the library's own source.
3. You showed that the bad case cannot happen. You followed the failure step by step, and it does not get there.
4. You ran it: a script or a test that calls the real code and fails loudly if you are wrong.
5. You reproduced it in the running app.

Step 4 is usually one small script that imports the same library that the app ships and calls the exact function that you are worried about.

## Steps

1. Read the change: the diff, the symbols that it adds, changes, and deletes, and what it now does differently, including the part that the diff does not show. Get the pull request and its commits.
2. Find the one fact that makes it safe. Most changes that look risky are safe because of one fact, such as "this call only drops cache entries that are already dead, and does nothing else". Find that fact. If it holds, it clears most risky cases at once. Spend your time here, not on a long list of maybes.
3. Look where a search stops. Read the source of the library that you call, and check its pinned version and any local patch. Work out when things run: microtasks, unmount and teardown, or the framework's update order. Follow what a symbol search misses: the JSON that an API returns, a database column, a wire format, another language that reads the same bytes, a feature flag, or code three calls away.
4. Be honest about each risk. Give it a real chance of happening and a real cost if it does. Keep the risks that you confirmed. List the risks that you checked and cleared separately. Cite a real `file:line`. A search that finds nothing is still an answer. Never invent a caller or an API.
5. Prove the one fact. Write a script or a test that runs the real code, run it, and paste what happened.
6. For a big or wide change, run it as an **arena**. Ask more than one model the same question and combine the answers. Different models catch different real bugs.

## What to hand back

- **What it does**: what changed, including the part that is not obvious.
- **The one fact that makes it safe**: state it, say which step of the list you got it to, and show the proof. If you could not prove it, write "unproven".
- **Risks**: for each, how it breaks, the `file:line`, how likely and how bad it is, and how to check it. Paste the proof for the risks that matter.
- **Cleared**: what you checked, and why it is fine.
- **Before you merge**: the cheapest test or reproduction that catches the real bug, including the script that you wrote.

Write it with the **clean-text** skill, cite real code, and remove anything private before it goes anywhere public.

**Reply:** the write-up above, with the one safety fact either proven or marked unproven.
