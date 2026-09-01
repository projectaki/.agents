## What changed

<!-- Final behavior only, as concise bullets. Include compatibility or migration
work. Do not list files or work history. State the accepted scope of the change
here. Do not refer to the developer in the third person or invent a collective
team voice. -->

## Blast radius

<!-- State which surfaces the change reaches and how far a failure would spread.
State the widest single code path the change touches. State what a failure looks
like for a user. State whether rollback rewrites data, whether a database
migration ships, and whether redeploying the previous build is sufficient. -->

## Regression assurance

<!-- One row for every behavioral path and material regression concern in the
canonical assurance report. Use human names, never internal IDs. -->

| Behavior at risk | Affected surface | Evidence | Verdict | Residual risk or waiver |
|---|---|---|---|---|
| <!-- Observable regression --> | <!-- User, API, component, system, contract, data, or operations --> | <!-- Automated: test permalink + command and result; Inspection: explanation + final-code permalink; Manual: reason + public artifact --> | <!-- Pass or Waiver accepted --> | <!-- None, remaining risk, or accepted waiver --> |

## Manual test steps

<!-- Optional. Remove this heading when no manual check is needed. Include it
only for behavior without automated coverage or for a check that a reviewer
must do before approval. Split the checks into "### Developer checks" and
"### Reviewer checks". Make each step one concrete, observable check. -->
