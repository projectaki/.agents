# Type System Discipline

Make the compiler reject impossible states, mixed-up primitive values, and cases that are not handled.

- Give meaningful primitives their own type. If two arguments have the same primitive type but different meanings, give each its own type. Validate the value once when you create it.
- External data has no type until you parse it. JSON, RPC payloads, CLI arguments, config, environment variables, and database rows go through a parse function at the boundary that returns the typed model.
- Derive types from the schema that owns the shape. Do not write a second, parallel type by hand.
