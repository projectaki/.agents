# PR Verification Report

## Scope

- **Why:** <intended outcome>
- **Changed:** <behavior and implementation>
- **Affected:** <users, systems, contracts, data, operations>
- **Unchanged:** <important neighboring behavior>

## Behavior

| Scenario | Method | Result | Evidence |
|---|---|---|---|
| <acceptance criterion> | <command or flow> | Pass/Fail | <artifact or observation> |

## Visual comparison

| State | Before | After | Result |
|---|---|---|---|
| <state or flow> | <artifact> | <artifact> | <unchanged, intended change, or regression> |

Note the evidence run, whether interaction map/viewport/fixtures matched, and
any intentional differences. Omit this section when not applicable.

## CI parity

| Job / variant | CI source | Local command | Result | Evidence |
|---|---|---|---|---|
| <job> | <workflow:line> | <command> | Pass/Fail/Unrun/CI-only | <evidence or reason> |

- **Local parity:** <complete/incomplete>
- **Remote CI:** <passed/pending/failed/not supplied>

## Regression confidence

| Risk | Evidence | Confidence |
|---|---|---|
| <possible regression> | <test, flow, comparison, or log> | High/Medium/Low |

For bugs, include the original reproduction before and after the change. Say
only that no regressions were observed in the verified scope.

## Gaps

- **Skipped or CI-only:** <check and reason>
- **Environment differences:** <local versus CI>
- **Residual risk:** <remaining unknowns>
- **Human decision:** <approval, exception, or more evidence>
