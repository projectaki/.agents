# Testing

## Unit Tests

Always write unit tests for:

- pure functions
- deterministic business logic
- validation
- utility functions

Unit tests should be:

- isolated
- deterministic
- fast

---

## Integration Tests

While designing systems, always think about future integration testing.

Favor designs that make integration testing straightforward.

Clearly separate business logic from infrastructure to simplify testing.

## Test Behavior, Not Implementation

A test is a claim about what the code does for its users. A user is a caller, an end user, or another service.

- Behavior is what users can observe through the interface that they use: return values, errors, state that they can read back, and effects on outside systems, such as a request sent, a row written, or a message emitted.
- Implementation is what users cannot observe: private helpers, the internal order of calls, intermediate data, and which internal part did the work.

Judge each test against two imagined edits:

1. Break the behavior. Make the code return a wrong value, skip an effect, or do the effect twice. If the test still passes, it proves nothing. Common causes are an assertion that is looser than the contract, an expected value that the code under test calculated, a repeated constant or prompt string that never runs the code that reads it, and an assertion on data that the test built itself.
2. Change the internals. Keep each observable result the same and restructure the code. If the test now fails, it is tied to the implementation. It needs a rewrite on each refactor and still catches no bug.

Keep a test that catches the first edit and survives the second. Rewrite or delete the other tests.

To write such a test, drive the code through the interface that its users use, with a concrete input. Derive the expected value from the requirement, not from a run of the code. Assert exactly what the contract promises, no less and no more.

The contract decides what counts as behavior, not the shape of the assertion:

- If the promise is "an empty cart never charges", an assertion that the payment client got no call is behavior. Add a case where the charge happens, so that the test proves it can see a call.
- The payload that a mocked external service receives is behavior, because that service sees it. A call to an internal helper is implementation.
- An empty list is the exact answer when no record matches. It is a weak check when the test only needs some result.
- An exact error message ties the test to wording that no caller reads. The error type that callers check is the contract.
- A test can check an invariant instead of a call, such as a key that must exist in two tables, or a compile-time type check. The invariant is the behavior.
