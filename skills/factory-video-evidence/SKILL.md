---
name: factory-video-evidence
description: "Create one reviewer-facing video and repeatable script for one supplied user-interface workflow that requires visual evidence. Use the supplied evidence workspace, environment, and authentication configuration without changing product code."
---

# Factory Video Evidence

## Purpose

Turn one supplied user-interface workflow into one repeatable script and one
compact video.

## Inputs

Require:

- one workflow with stable risk and behavioral-path identifiers
- the reason automation is insufficient or a direct human video requirement
- an evidence workspace at `<evidence>/<project>/<git-branch-name>/` with
  `workflows/` and `publish/` directories
- a project `_auth/` directory with instructions, saved states, and permitted
  dummy test credentials
- start URL, preconditions, actions, and observable result
- project data setup and cleanup instructions
- `playwright-cli` on `PATH`

Reject multiple workflows, missing required inputs, or a workflow that supplied
automation already proves.

## Operation

1. Work only in the supplied evidence workspace. Do not initialize another
   workspace or overwrite an existing script or video.
2. Follow `_auth/instructions.md`. Use `_auth/credentials.env` only for dummy
   test credentials. Restore the named state from `_auth/states/`.
   Reauthenticate when it is missing or expired. Save refreshed state there
   with mode `0600`.
3. Use the supplied project data setup and cleanup. Do not assume a database or
   command-line interface.
4. Discover the workflow without recording in a unique browser session. Restore
   authentication before navigation. Take semantic snapshots before using
   references and after navigation or material interface changes.
5. Capture emitted semantic Playwright code. Close the discovery session.
6. Write `workflows/<workflow-id>.js` as `async page => { ... }` for
   `playwright-cli run-code --filename`. Use semantic locators and explicit
   observable checks that throw. Avoid sleeps, fragile CSS, incidental
   navigation, and hidden dependencies.
7. Run without video until the script passes from the required initial state:

   ```bash
   <skill-directory>/scripts/run_cli_workflow.sh \
     --session <unique-check-session> \
     --url <start-url> \
     --script workflows/<workflow-id>.js \
     --state <auth-directory>/states/<profile>.json
   ```

8. Reset the same initial state and record the passing script once:

   ```bash
   <skill-directory>/scripts/run_cli_workflow.sh \
     --session <unique-record-session> \
     --url <start-url> \
     --script workflows/<workflow-id>.js \
     --state <auth-directory>/states/<profile>.json \
     --video publish/<workflow-id>-<short-name>.webm \
     --test-case '<workflow-id>: <short description>'
   ```

   Omit `--state` only when the authentication instructions permit it.
   `--test-case` is optional and must contain no sensitive data. The runner must
   close only its own session and retain a failed or interrupted video. Never
   use `close-all` or `kill-all`.
9. Review the complete video for the expected result, compactness, and sensitive
   data. Retain and report a failed recording. Confirm all sessions are closed.

A flaky, partial, inferred, retried, or inaccessible workflow does not pass.
Never expose authentication data in the workspace, script, result, or video.

## Outputs

Return a structured result and a concise human summary with:

- result: `pass`, `fail`, `blocked`, or `not-run`
- evidence workspace and authentication profile name without secrets
- risk and behavioral-path identifiers
- video rationale and observed result
- script and video paths when created
- cleanup, unmet requirements, and residual risk

For a pass, state only that no regression was observed in the supplied
workflow. State that video complements automated tests.

## Side effects

Start browser sessions. Interact with permitted test data. Refresh test
authentication state. Write the supplied workflow script and video. Perform the
supplied cleanup. Do not change product code.

## Failure results

Return `not-run` when the workflow is automatable or an input is missing. Return
`blocked` for inaccessible authentication, environment, or required tooling.

## Non-goals

Do not accept multiple workflows, change product code, or perform a review.
