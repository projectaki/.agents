---
name: factory-video-evidence
description: "Create one reviewer-facing video for one supplied video-required UI workflow in an existing evidence run. Use only when implementation review explains why automation is insufficient or the human explicitly requires video."
---

# Factory Video Evidence

Turn 1 supplied UI workflow into 1 repeatable script and 1 compact video. Do not
accept multiple workflows, change product code, or perform implementation
review.

When orchestrated, the primary thread must delegate this skill to the routed
tier worker. That worker must not spawn another lifecycle actor.

## Workflow

1. Require 1 `video-required` UI workflow, stable risk ID, behavioral path IDs,
   reason automation is insufficient, existing run path, project `_auth`
   directory, start URL, preconditions, actions, and observable result. A direct
   human requirement is a valid reason. Return missing or automatable coverage.
2. Require `<evidence>/<project>/<git-branch-name>/` with `workflows/` and
   `publish/`, and `_auth/` under the project root. Work inside this run. Do not
   initialize another run or overwrite its script or video.
3. Follow `_auth/instructions.md`. Use `_auth/credentials.env` only for dummy
   test credentials. Restore the named state from `_auth/states/`; if missing
   or expired, reauthenticate before recording, save it there, and set mode
   `0600`. Never expose auth in the run, script, output, or video.
4. Use the project's data setup and cleanup. Do not assume a database or CLI.
5. Require `playwright-cli` on `PATH`. Discover without recording in a unique
   session. Restore auth before navigation; snapshot before refs and after
   navigation or material UI changes. Capture emitted semantic Playwright code,
   then close the session.
6. Write `workflows/<workflow-id>.js` as `async page => { ... }` for
   `playwright-cli run-code --filename`. Use semantic locators and explicit
   observable checks that throw. Avoid sleeps, fragile CSS, incidental
   navigation, and hidden dependencies.
7. Run without video until the script passes from the required initial state:

   ```bash
   ~/.agents/skills/factory-video-evidence/scripts/run_cli_workflow.sh \
     --session <unique-check-session> \
     --url <start-url> \
     --script workflows/<workflow-id>.js \
     --state <auth-directory>/states/<profile>.json
   ```

   Omit `--state` only when auth instructions allow it. Flaky, partial,
   inferred, retried, or inaccessible workflows do not pass.
8. Reset the same initial state and record the passing script once:

   ```bash
   ~/.agents/skills/factory-video-evidence/scripts/run_cli_workflow.sh \
     --session <unique-record-session> \
     --url <start-url> \
     --script workflows/<workflow-id>.js \
     --state <auth-directory>/states/<profile>.json \
     --video publish/<workflow-id>-<short-name>.webm \
     --test-case '<workflow-id>: <short description>'
   ```

   `--test-case` is optional, must contain no sensitive data, and adds a
   translucent label that survives navigation. The runner closes only its
   session and keeps failed or interrupted video for review. Never use
   `close-all` or `kill-all`.
9. Review the whole video for the expected result, compactness, and sensitive
   data. Report and retain failed recordings. Confirm all 3 sessions are closed.

## Output

Return the run path, auth profile name without secrets, risk and path IDs,
video rationale, result (`pass`, `fail`, `blocked`, or `not-run`), observation,
script path, video path if recording began, cleanup, unmet requirements, and
residual risk.

Report final state, not attempt history. For a pass, say only that no regression
was observed in that workflow; video complements automated tests.
