# Boundary Discipline

Validate data, narrow its type, and handle errors where the data crosses a system boundary, such as CLI arguments, config files, external APIs, and the network. Inside the system, trust the types. Do not validate again, and do not add null checks for data that the boundary already validated. Parse raw data into domain types at the boundary. Do not expose transport or framework types in the public interface. Put business logic in pure functions with no framework dependencies. Keep the outer layer that calls them thin.

Use two tests. Is this data crossing a boundary now? If not, the validation is redundant. Can this be a pure function that the outer layer only calls? If yes, extract it.
