# Stored credentials and protected operations

Use these examples when a change stores credentials, selects accounts, verifies
signatures, or mutates a protected resource. Adapt the checks to the actual
contract. Do not assume that a passing signature check establishes ownership.

Trace one request through credential storage, account selection, signature
verification, resource ownership, and the final mutation. Identify the component
that enforces each rule. Check affected unchanged callers too.

For example, an update endpoint can select a stored account token and use it to
verify a request signature. If a blank token causes verification to be skipped,
an account record with missing credentials can allow an unauthorized update.
Check that rejection occurs before the mutation and preserves existing data.

Check the relevant cases:

- Missing, empty, or whitespace-only credentials cannot bypass verification.
- Duplicate account matches follow an explicit selection rule or fail safely.
- A valid credential for another owner cannot authorize the current resource.
- A URL mismatch cannot select another account or bypass the ownership rule.
  Apply the application's documented URL normalization rules.
- Invalid or missing signatures reject protected mutations. Valid signatures
  still require the correct account and resource owner.

Use isolated tests for credential validation and account selection. Use an
integration test through the protected operation to verify that storage,
selection, signature verification, ownership, and mutation enforce the same
contract. Test substitutes must preserve rejection behavior.

Report a defect only with a supported trigger and impact. If the expected rule
is unclear, state the missing requirement. Passing examples do not prove that
all security defects are absent.
