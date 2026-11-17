# Type System Discipline

Make the compiler reject impossible states, mixed-up primitive values, and cases that are not handled. Where possible, design errors and special cases out of existence. Do not add more handlers for them.

- Give meaningful primitives their own type. `UserId` and `OrderId` can both be strings, but they must not be interchangeable. Use a branded type in TypeScript or a newtype in other languages. Validate the value once when you create it, then trust the type. If two arguments have the same primitive type but different meanings, give them separate types.
- Parse external data into typed models at the boundary, according to [Boundary discipline](boundary-discipline.md).
- Derive types from the schema that owns the shape. When a protobuf file, an OpenAPI spec, a GraphQL schema, a database migration, or a design-token file defines a shape, generate or derive the type from it. Do not write a second, parallel type by hand.
