---
name: factory-evidence
description: "Use when the human explicitly requests evidence collection or when factory-verify invokes it with a regression-scope packet. Execute its manual UI, API, CLI, worker, or other regression test cases; record observed results; capture sanitized evidence; and return case-level results for verification and the draft PR without modifying product code."
---

# Factory Evidence

Execute the supplied `$factory-regression-scope` packet and preserve reviewable
proof.

## Safety

- Keep runs outside the repository under
  `$HOME/evidence/<project>/<thread-name>/<timestamp>/`.
- Keep credentials, sessions, raw responses, logs, and failed captures in
  owner-only `private/` or unpublished `working/`; never record secret values.
- Put only reviewed, sanitized artifacts in `publish/`.
- Get approval before destructive, irreversible, credentialed, production-data,
  or externally consequential scenarios.

## Workflow

1. Read the complete scope packet and repository test instructions. Reject stale
   scope or return missing prerequisites before testing.
2. From the project, initialize one run:

   ```bash
   python3 ~/.agents/skills/factory-evidence/scripts/init_evidence_run.py \
     --thread <thread-name>
   ```

3. Create a results ledger containing every manual test ID and title from the
   scope packet, initially marked `not-run`. Execute every reachable case in
   packet order using its stated fixtures and environment. Do not rename,
   combine, omit, or silently add cases; record exact deviations and report new
   scope gaps separately.
4. For UI flows, rehearse before recording and capture only stable states that
   prove the expected behavior. For APIs and other surfaces, save sanitized
   commands, status, assertions, and relevant output. Keep troubleshooting and
   sensitive raw material unpublished.
5. Mark each case `pass`, `fail`, `blocked`, or `not-run`. Record the actual
   observed result even when it matches the expectation. A pass requires direct
   observation of every expected result and case-specific proof; inaccessible,
   partially exercised, or inferred behavior is not a pass.
6. Review every artifact and create `publish/manifest.md` with one row per test
   ID: surface, test-case title, result, observed result, and sanitized evidence.
   Use the same IDs and order as the scope packet, account explicitly for
   blocked and not-run cases, and label artifacts with their test ID.

## Output

Return the run path, environment, complete manual-test results ledger, evidence
locations, deviations, failures, blockers, not-run cases, scope gaps, cleanup
status, and residual risk. Make the ledger directly reusable by
`$factory-verify` and `$open-draft-pr`. Do not edit product code or start another
lifecycle. Upload only sanitized `publish/` contents and delete the run after
use or abandonment.
