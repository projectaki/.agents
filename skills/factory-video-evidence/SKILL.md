---
name: factory-video-evidence
description: "Create compact reviewer-facing videos of supplied UI workflows with deterministic playwright-cli scripts. Use for UI regression evidence before a pull request."
---

# Factory Video Evidence

Turn supplied UI workflows into short, repeatable videos for code review. Do not
modify product code or discover regression scope here.

## Workflow

1. Read the supplied workflows and repository instructions. Require each
   workflow to have a stable ID, preconditions, actions, and observable expected
   result. Return missing or non-UI coverage to the caller.
2. Create a run outside the repository:

   ```bash
   python3 ~/.agents/skills/factory-video-evidence/scripts/init_video_evidence_run.py \
     --thread <thread-name>
   ```

   Change into the returned run directory before creating or executing scripts.

3. Confirm `playwright-cli` is on `PATH`. Use a fresh named CLI session to
   discover each workflow without recording: open its start URL, snapshot the
   page, perform its actions, and capture the semantic Playwright code emitted
   by the CLI. Re-snapshot after navigation or material UI changes.
4. Write the resulting action code to
   `workflows/<workflow-id>.js` as an `async page => { ... }` function for
   `playwright-cli run-code --filename`. Use semantic locators and explicit
   observable checks that throw on failure. Avoid fixed sleeps, fragile CSS
   selectors, incidental navigation, and dependencies between workflows.
5. From a fresh known initial state, run the script without video until it
   passes. A flaky, partial, inferred, retried, or inaccessible workflow does
   not pass.

   ```bash
   export PLAYWRIGHT_CLI_SESSION=<workflow-id>-check
   playwright-cli open <start-url>
   playwright-cli run-code --filename=workflows/<workflow-id>.js
   playwright-cli close
   ```

6. Prepare the same initial state in a fresh session, then record one execution
   of the exact passing script. Start recording only after unrelated setup and
   navigation so the video begins at the first meaningful UI step. Stop and
   discard the recording on any failure. If the script changes, pass it again
   before recording.

   ```bash
   export PLAYWRIGHT_CLI_SESSION=<workflow-id>-record
   playwright-cli open <start-url>
   playwright-cli video-start publish/<workflow-id>-<short-name>.webm
   playwright-cli run-code --filename=workflows/<workflow-id>.js
   playwright-cli video-stop
   playwright-cli close
   ```

7. Watch every published video. It must show the complete workflow and expected
   result, contain no secrets or sensitive data, and be as short as the workflow
   allows. Keep only one final video per passing workflow in `publish/` and
   close every CLI session.

## Output

Return the run path and one result per supplied workflow: `pass`, `fail`,
`blocked`, or `not-run`; the observed result; the Playwright script; and the
published video when passed. Report deviations, missing coverage, cleanup, and
residual risk. Say only that no regression was observed in the recorded
workflows; video evidence complements rather than replaces automated tests.
