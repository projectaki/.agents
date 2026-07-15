---
name: capture-pr-evidence
description: "Capture concise, temporary UI evidence for pull requests: meaningful screenshots, compact walkthroughs, and comparable before/after states. Use for UI context, bug reproduction, regression checks, and feature verification without storing evidence or private sessions in the repository."
---

# Capture PR Evidence

Create visual evidence a reviewer can understand and compare quickly.

## Safety

- Keep the entire run outside the repository under
  `${TMPDIR:-/tmp}/codex-pr-evidence/<project>/<run>/`.
- Keep credentials, cookies, tokens, and browser state in `private/` with
  owner-only permissions. Never record or upload secret values.
- Keep discovery notes, tool state, logs, snapshots, and failed captures in
  `working/`. Configure tools such as Playwright to write there.
- Put only reviewed, sanitized artifacts in `publish/`. Check for personal or
  customer data, autofill, notifications, unrelated tabs, and secrets.
- Delete the run after upload or abandonment.

## Start

Run from the project:

```bash
python3 ~/.agents/skills/capture-pr-evidence/scripts/init_evidence_run.py
```

The script creates `private/`, `working/`, `publish/screenshots/`, and
`publish/videos/`. Use one run for the complete comparison, naming artifacts
`before-*` and `after-*`.

## Capture

1. Define the smallest flow and meaningful states that prove the behavior.
2. Restore an existing session when possible. Save browser storage in `private/`;
   capture `sessionStorage` separately when the tool's storage state omits it.
   Record only how credentials can be obtained again, never their values.
3. Explore without recording. Write `working/interaction-map.md` with the start
   state, actions/selectors, readiness waits, expected states, capture points,
   test data, and cleanup.
4. Rehearse, clean up, reset, and wait for a stable start state.
5. Record only the proving flow. Exclude login, builds, troubleshooting, and long
   waits. Aim for 30–90 seconds per focused flow; split unrelated flows.
6. Capture only distinct states with stable viewport and framing. Keep polished
   output in `publish/` and raw attempts in `working/`.
7. Review every frame and create `publish/manifest.md` describing the project,
   environment, before/after designation, what each artifact proves, capture
   setup, omissions, and cleanup status.

At verification, repeat the same interaction map, viewport, fixtures, and
capture points. Compare behavior and timing, not pixel identity, and explain
intentional differences.

## Fail safely

Stop repeated auth attempts when a session cannot be restored. Recapture any
private data. Keep failed or long recordings in `working/`. Capture an app-start
failure only when it helps unblock the work.

## Finish

Before upload, enumerate `publish/` and confirm nothing from `private/` or
`working/` is selected. Report the run path, publishable artifacts, what each
proves, session-restoration status, cleanup status, evidence gaps, and residual
risk. Upload only sanitized `publish/` contents, then delete the run when it is
no longer needed.
