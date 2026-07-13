---
name: factory-verify
description: "Use only when the human explicitly starts the verification lifecycle and supplies the task, approved plan, implementation packet, and relevant bug baseline, to verify behavior with tests and observable evidence while treating unrun checks as unknown."
disable-model-invocation: true
---

# Factory Verify

Prove implemented behavior within this lifecycle. Initial bug reproduction is
outside this lifecycle.

## Input

Require the task and acceptance criteria, approved plan, implementation packet,
current branch or diff, and repository verification instructions. For a bug fix,
also require the applicable replication baseline. If the evidence needed to
define verification is missing, return `inconclusive` with the input gap.

## Environment Policy

- Cover the `verification-engineer` role and add `user-simulator` for
  user-visible behavior. Delegate only when authorized by the user and
  repository policy and suitable subagents are available; otherwise perform
  those roles in the main session.
- Treat read-only or otherwise capability-restricted subagents as analysis
  support. Run tool-dependent verification in an authorized capable session.
- Treat browser, simulator, device, GUI, network, and other access-controlled
  tools as conditional. Use Playwright only when it and the target are reachable
  without permission, sandbox, or access-control failures.
- Make at most one cheap availability check and one ordinary attempt. After a
  missing tool or clear access failure, stop retrying. Do not install tools or
  seek elevated access solely for optional evidence.
- Use reachable alternatives such as existing tests, HTTP requests, CLI flows,
  logs, available browser tooling, existing screenshots, or manual steps.

## Workflow

1. Read the task, approved plan, implementation summary, and current diff.
2. For a bug fix, read the human-supplied minimal replication baseline. Before
   rerunning it, re-evaluate safety and confirm that any destructive, irreversible,
   production-data, credential, or externally consequential step still has
   explicit human authority. Otherwise skip it or return `blocked`.
3. Run targeted checks first, then broader checks required by the repository.
4. Exercise externally observable behavior when feasible.
5. Capture concise, reproducible evidence and synthesize one packet.

## Verification Rules

- Treat unrun checks as unknown, not passed.
- Distinguish changed-code failures from pre-existing or environment failures.
- A skipped optional check does not fail verification; report its concrete
  reason, evidence gap, fallback, and residual risk.
- If an inaccessible check is required to establish an acceptance criterion,
  return `inconclusive` or `blocked`, never `pass`.
- For iOS simulator evidence, require macOS (`Darwin`) and reachable simulator
  access. Otherwise skip it under the environment policy.
- Capture before/after evidence for visible bug fixes when feasible.
- Sanitize evidence. Do not retain secrets, credentials, tokens, personal data,
  or sensitive production data in logs, screenshots, commands, or artifacts.

## Output

Return:

- verdict: `pass`, `fail`, `inconclusive`, or `blocked`
- commands or methods run
- user-level scenarios tested
- results and evidence
- bug baseline before/after result, when applicable
- failures and likely cause
- skipped checks, reasons, fallbacks, evidence gaps, and residual risk
- decisions or remaining evidence requiring human action

## Stop Condition

Stop when the verification packet and verdict are complete, or when required
evidence is unavailable and the verdict is `inconclusive` or `blocked`. Return
the packet to the human. Do not invoke review, merge, release, or another factory
skill and do not start another lifecycle.
