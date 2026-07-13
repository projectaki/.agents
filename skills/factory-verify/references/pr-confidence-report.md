# PR Verification and Regression Confidence

## Change scope

- **Why:** <problem or intended outcome>
- **What changed:** <concise behavior and implementation summary>
- **Affected areas:** <slices, systems, contracts, users, data, operations>
- **Intentionally unchanged:** <important neighboring behavior outside scope>

## Acceptance and behavior evidence

| Scenario or criterion | Method | Result | Evidence |
|---|---|---|---|
| <criterion> | `<command or observable flow>` | Pass/Fail | <artifact or concise evidence> |

## CI parity

| CI job / matrix variant | CI source | Local equivalent | Result | Evidence |
|---|---|---|---|---|
| <job> | `<workflow:line>` | `<exact command>` | Pass/Fail/Unrun/CI-only | <evidence or reason> |

- **Local CI parity:** <complete/incomplete>
- **Remote CI status:** <passed/pending/failed/not supplied>

## Regression confidence

| Risk considered | Why it could regress | Evidence | Confidence |
|---|---|---|---|
| <risk> | <impact path> | <test, scenario, comparison, log, or artifact> | High/Medium/Low |

For bug fixes, include the original reproduction result before and after the
change. State only that no regressions were observed within the verified scope.

## Gaps and residual risk

- **Skipped or CI-only checks:** <check and concrete reason>
- **Environment differences:** <local versus CI differences>
- **Residual risk:** <what remains unknown and why>
- **Human decision needed:** <approval, exception, or additional evidence>
