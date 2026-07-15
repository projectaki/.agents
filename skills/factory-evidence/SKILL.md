---
name: factory-evidence
description: "Use when the human explicitly requests evidence collection or when factory-verify invokes it with a regression-scope packet. Execute manual UI, API, CLI, worker, or other regression scenarios; capture sanitized evidence; and return scenario-level results without modifying product code."
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

3. Execute every reachable scenario in packet order using its stated fixtures
   and environment. Record exact deviations.
4. For UI flows, rehearse before recording and capture only stable states that
   prove the expected behavior. For APIs and other surfaces, save sanitized
   commands, status, assertions, and relevant output. Keep troubleshooting and
   sensitive raw material unpublished.
5. Mark each scenario `pass`, `fail`, `blocked`, or `not-run`. A pass requires an
   observed expected result; inaccessible or inferred behavior is not a pass.
6. Review every artifact and create `publish/manifest.md` mapping scenario IDs
   to results and evidence. Report newly discovered scope gaps without silently
   expanding the packet.

## Output

Return the run path, environment, scenario results, evidence locations,
deviations, failures, blockers, skipped scenarios, scope gaps, cleanup status,
and residual risk. Do not edit product code or start another lifecycle. Upload
only sanitized `publish/` contents and delete the run after use or abandonment.
