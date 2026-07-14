---
name: capture-pr-evidence
description: "Capture concise, temporary UI evidence for pull requests: rehearse a feature, record compact before-and-after videos, take screenshots of meaningful states, preserve restorable browser sessions safely, and prepare sanitized artifacts for PR upload. Use for frontend investigations, bug reproduction, regression checks, feature verification, or any task that needs visual evidence without storing artifacts in the repository."
---

# Capture PR Evidence

Create visual evidence that reviewers can understand quickly and compare before and after a change. Keep all working files outside the repository and treat authentication material as private, disposable state.

## Non-negotiable rules

- Store evidence under `${TMPDIR:-/tmp}/codex-pr-evidence/<project>/<run>/`, never in the repository.
- Configure automation-tool state directories outside the checkout. In particular,
  keep generated `.playwright-cli` logs and page snapshots under `working/` rather
  than allowing `.playwright-cli/` to remain at the repository root.
- Never write passwords, tokens, cookies, or secret values into notes, manifests, screenshots, videos, shell history, or committed files.
- Keep private session material in `private/` with owner-only permissions. Never upload that directory to a PR.
- Upload only the sanitized contents of `publish/` after reviewing them for secrets and personal data.
- Explore and rehearse before recording. Do not make discovery, login, builds, troubleshooting, or long waits part of the final video.
- Remove disposable evidence after successful upload or when the task is abandoned.

## Initialize a run

From any directory inside the project, run:

```bash
python3 ~/.agents/skills/capture-pr-evidence/scripts/init_evidence_run.py
```

Pass `--project`, `--run`, or `--base` when automatic names or the default temporary root are unsuitable. The script prints the run directory and creates:

```text
<run>/
├── private/       # browser state and secret references; never upload
├── publish/
│   ├── screenshots/
│   └── videos/
└── working/       # interaction map, rehearsal notes, raw captures
```

Use one run for a coherent before-and-after comparison. Put baseline and final files in clearly named groups such as `before-*` and `after-*`.

## Capture workflow

### 1. Define the evidence contract

Identify the user-visible behavior and the smallest sequence proving it. Decide which states matter before opening the recorder. Typical states are initial, empty/form, filled or validation, success/list, detail, confirmation, error, and final cleanup. Capture only states that help establish behavior or reveal a regression.

### 2. Restore or establish access

Prefer an existing authenticated session. If credentials are needed, obtain them from an approved secret source or the human and use them only at runtime.

In `private/credential-reference.md`, note only how access can be obtained again, for example:

```markdown
- Account purpose: local test administrator
- Identifier source: HUMANRISKS_TEST_EMAIL environment variable
- Secret source: team vault item "Local test administrator"
- Auth environment: local Auth0 tenant
```

Do not record the identifier or secret value. If no durable source exists, write `Ask the human again`.

Save browser cookies/local storage using the automation tool's storage-state feature. Some applications keep authentication or tenant selection in `sessionStorage`, which standard storage-state files may omit; export that separately when required. Restore storage state when launching the browser and inject session storage for the correct origin before visiting protected routes. Verify the restored session with a harmless authenticated page before recording.

Use descriptive private filenames such as `private/browser-state.json` and `private/session-storage.json`. Set permissions to `0600`. Session files are temporary secrets, even for local authentication.

### 3. Explore without recording

Navigate the entire feature once. Discover stable selectors, route transitions, loading behavior, modal behavior, and cleanup actions. Record an interaction map in `working/interaction-map.md` with:

- starting URL and prerequisite state
- ordered user actions
- stable selectors or accessible names
- expected state after each action
- waits that reflect application readiness rather than fixed delays
- data created and how it will be removed
- candidate screenshot points

Resolve environment and navigation problems during this phase.

### 4. Rehearse and reset

Run the sequence again without recording. Remove test data, return to the intended starting route, close overlays, and wait until the UI is stable. Use deterministic, obviously temporary data. Confirm the cleanup path before creating more data.

### 5. Record the compact walkthrough

Start recording only when the first meaningful page is ready. Perform the mapped sequence at a credible user pace:

- move directly between actions
- use readiness checks instead of arbitrary sleeps
- pause only long enough for state changes to be perceptible
- omit login and setup unless authentication itself is the feature
- stop immediately after the final proving state

Aim for 30–90 seconds per focused flow. Split independent behaviors into separate videos rather than producing a long tour. A slightly slower comprehensible action is better than an unnaturally fast click.

Save the polished recording directly in `publish/videos/`. Keep raw or failed recordings in `working/`, not `publish/`.

### 6. Capture state screenshots

Take screenshots at the preselected meaningful states. Use a stable viewport and consistent framing so before/after images are comparable. Prefer the application region or full browser viewport when surrounding context matters. Name files in sequence, for example:

```text
publish/screenshots/before-01-empty-list.png
publish/screenshots/before-02-filled-form.png
publish/screenshots/before-03-detail.png
publish/screenshots/after-01-empty-list.png
```

Do not create several screenshots that communicate the same state. Capture failures as well as successful states when the failure is the evidence.

### 7. Sanitize and describe

Review every publishable frame for secrets, tokens, email addresses, customer data, browser autofill, notifications, and unrelated tabs. Recapture or redact unsafe artifacts before upload.

Create `publish/manifest.md` containing:

- project and run label
- feature and environment
- baseline or final designation
- exact behavior demonstrated by each artifact
- viewport/browser when relevant
- known limitations or omitted states
- confirmation that temporary test data was cleaned up

Do not include credential values, session paths, or private implementation notes.

### 8. Compare, upload, and dispose

At verification time, repeat the same interaction map, viewport, fixtures, and screenshot points. Compare behavior and timing, not merely pixel identity. Explain intentional UI differences in the PR.

Before upload, enumerate files under `publish/` and confirm no file from `private/` or `working/` is selected. Upload the baseline and final evidence to the PR with short labels. Once the upload is confirmed and no local follow-up is needed, delete the entire run directory.

## Failure handling

- If the app cannot start, capture one concise failure screenshot or log excerpt only when it helps the human unblock the environment.
- If authentication cannot be restored, stop before repeated login attempts and report the missing secret source or auth configuration.
- If recording introduces long waits, keep the raw capture in `working/`, refine the interaction map, reset, and record again.
- If private data appears in a capture, do not upload it; recapture from a sanitized state.

## Handoff checklist

Report the absolute temporary run path, the publishable artifact list, what each artifact proves, whether session restoration works, and whether cleanup is complete. Explicitly state any evidence gap or residual regression risk.
