# Error Handling

Always design every code path.

Consider:

- expected failures
- unexpected failures
- retries
- validation
- propagation
- recovery

Errors should be explicit and meaningful.

Validate at system boundaries, according to [Boundary discipline](boundary-discipline.md).

Make retries and recovery safe, according to [Make operations idempotent](make-operations-idempotent.md).
