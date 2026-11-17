# Boundary Discipline

Validate data, narrow its type, and handle errors at the system boundaries. Inside the system, trust the code. Put business logic in pure functions. Keep the outer layer that talks to the outside world thin and mechanical.

Validation that is spread across the code is noisy and repeated, and it gives a false feeling of safety. Business logic that stays out of framework wiring can be tested without the framework.

- At the boundaries, such as CLI arguments, config files, external APIs, and network protocols: validate, return errors, and handle input defensively.
- Inside the system: use typed data and pass errors on. Do not validate again. Trust the types.
- Across the boundary: expose domain concepts, not the boundary's internal formats. Keep general mechanisms inside and special-purpose policy at the edge.

## Validation and errors

- Validate config when you parse it, not inside business logic.
- Parse raw data into domain types at the boundary.
- Do not expose transport, storage, framework, or wire types in the public interface.
- Do not add null checks deep in a call chain when the boundary already validated the data.

## Code organization

- Keep business logic in pure functions with no framework dependencies.
- Make parsing a pure transformation from raw input to typed state.
- Make prompt building a pure transformation from structured state to a string.
- Make scoring and assessment pure transformations from state to results.

## Tests

- "Is this data crossing a system boundary now?" If not, validation is redundant.
- "Can this be a pure function that the outer layer only calls?" If yes, extract it.
