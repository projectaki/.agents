# Factory proof ledger

Use `proof-ledger.yaml` as the canonical record that preserves acceptance claims
and their proof obligations across lifecycles. Keep history in checkpoint
snapshots. Keep only the current claim state in the canonical file.

```yaml
schema_version: 1
task_revision: 1
updated_at: 2026-08-28T10:00:00Z
claims:
  - claim_id: AC-001
    statement: Every upload endpoint derives the organization on the server.
    source: intake/handoff.md
    status: active
    path_ids: [PATH-001]
    risk_ids: [RISK-001]
    inventory:
      status: closed
      items:
        - item_id: upload-questionnaire
          name: Questionnaire upload endpoint
          source: src/QuestionnaireController.cs
    proof_obligations:
      - proof_id: PROOF-001
        requirement: Reject an unknown questionnaire before storage access.
        required_method: automated
        planned_method: automated
        evidence: []
        verdict: unverified
        exception: null
```

Use stable identifiers. Never reuse an identifier for different behavior.

An active universal claim that uses `all`, `every`, or `each` requires a closed,
nonempty inventory. Reconcile each inventory item independently.

Use proof methods `automated`, `inspection`, `visual`, or `manual`. Planning may
not change `planned_method` from `required_method` unless the obligation has an
accepted exception:

```yaml
exception:
  status: accepted
  claim_ids: [AC-001]
  path_ids: [PATH-001]
  approval_reference: human decision recorded in planning/handoff.md
  residual_risk: The upload controller has no direct integration test.
```

An exception must name exact claims and paths. Related wording does not extend
its scope. Verification treats an unapproved exception as blocking.

Evidence entries must name `method`, `result`, `revision`, and a durable
`reference`. Use verdicts `unverified`, `pass`, `fail`, `inconclusive`, or
`waived`. A `pass` verdict requires evidence. A `waived` verdict requires an
accepted exception.

Validate the ledger with:

```bash
python3 <factory-handoff-directory>/scripts/validate-proof-ledger.py \
  <task-root>/proof-ledger.yaml
```
