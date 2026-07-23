---
name: factory-video-evidence
description: "Create one compact reviewer-facing video from one supplied video-required UI workflow inside an existing shared evidence run. Use only when regression scope explains why automated assertions are insufficient or when the human explicitly requires video evidence."
---

# Factory Video Evidence

Turn one supplied UI workflow into one repeatable script and one review video.
Do not accept multiple workflows, modify product code, or discover regression
scope.

## Workflow

1. Require exactly one `video-required` UI workflow, the reason automated
   evidence is insufficient, an existing evidence-run path, and its project
   `_auth` directory. Require the workflow to have a stable risk ID, start URL,
   preconditions, actions, and observable expected result. Accept a direct
   human requirement as the reason. Return missing or automatable coverage to
   the caller.
2. Validate that the run contains `workflows/` and `publish/`, then change into
   it. The run must be `<evidence>/<project>/<git-branch-name>/`, with `_auth/`
   under the project evidence root. Do not initialize another run. Refuse to
   overwrite an existing script or video for the workflow ID.

3. Read `_auth/instructions.md` as the source of truth for authentication. Use
   `_auth/credentials.env` only for dummy test credentials and restore the
   instructed file from `_auth/states/` when available. If state is missing or
   expired, reauthenticate outside the recording, save the refreshed state in
   `_auth/states/`, and set its mode to `0600`. Never copy auth material into
   the run, workflow script, command output, or video.
4. Use the project's existing test-data setup and cleanup mechanism when the
   workflow requires local data. Follow project instructions for the configured
   database rather than assuming a database engine or command-line client.
5. Confirm `playwright-cli` is on `PATH`. Discover the workflow without
   recording in a unique named session. Restore auth before navigation.
   Snapshot before using element refs and again after navigation or material UI
   changes. Capture the semantic Playwright code emitted by the CLI. Close the
   discovery session when done.
6. Write `workflows/<workflow-id>.js` as an `async page => { ... }` function for
   `playwright-cli run-code --filename`. Use semantic locators and explicit
   observable checks that throw on failure. Avoid fixed sleeps, fragile CSS
   selectors, incidental navigation, and hidden dependencies.
7. Use the bundled runner with a unique session name to execute the script
   without video until it passes from the required initial state:

   ```bash
   ~/.agents/skills/factory-video-evidence/scripts/run_cli_workflow.sh \
     --session <unique-check-session> \
     --url <start-url> \
     --script workflows/<workflow-id>.js \
     --state <auth-directory>/states/<profile>.json
   ```

   Omit `--state` only when the auth instructions say the workflow needs no
   authentication. A flaky, partial, inferred, retried, or inaccessible
   workflow does not pass.
8. Prepare the same initial state, then use the runner to record the exact
   passing script once:

   ```bash
   ~/.agents/skills/factory-video-evidence/scripts/run_cli_workflow.sh \
     --session <unique-record-session> \
     --url <start-url> \
     --script workflows/<workflow-id>.js \
     --state <auth-directory>/states/<profile>.json \
     --video publish/<workflow-id>-<short-name>.webm \
     --test-case '<workflow-id>: <short description>'
   ```

   `--test-case` is optional. When supplied, the runner injects a non-interactive
   HTML label in the top-left corner before recording. Its translucent background
   keeps the underlying UI visible, and the label is restored after navigation.
   Use test-case text that contains no secrets or other sensitive data.

   The runner stops recording and closes only its own session. It keeps the video
   at the requested path when the workflow fails or is interrupted so the failure
   can be reviewed. Never use `close-all` or `kill-all`.
9. Review every video for the complete workflow, expected result, compactness,
   and sensitive data. For a failed recording, report the failure and retained
   video path; the reviewer can inspect and delete it. Confirm the discovery,
   check, and recording sessions are closed.

## Output

Return the shared run path, auth profile used without secret values, workflow
risk ID, reason video was required, result (`pass`, `fail`, `blocked`, or
`not-run`), observed result, script path, video path when recording started,
cleanup status, deviations, and residual risk. Say only that no regression was
observed in a passing workflow; video evidence complements automated tests.
