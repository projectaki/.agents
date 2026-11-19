# TypeScript project structure

These rules apply to every TypeScript project unless I override them.

## Monorepo

Use a Turborepo monorepo with `apps/` and `packages/`.

### Apps

An app is an entry point into the system, such as `web`, `api`, `worker`, `dashboard`, `cli`, or `mobile`. An app is a thin layer that connects infrastructure, configuration, and the business logic. Business logic does not go in an app.

### Packages

Each project has a main package named `core`. It owns the domain models, business logic, services, use cases, interfaces, and vertical slices. Keep as much code as possible in `packages/core`.

Add another package only for a clear reason, such as:

- shared UI components
- generated SDKs
- infrastructure libraries that several apps use
- shared configuration
- test utilities

Do not split code into packages too early. Each package adds maintenance, dependency management, and reader load. One large, cohesive `core` package is better than many small packages.

## Vertical slices

Organize the application into vertical slices, not horizontal layers. A reader can understand a slice without reading other slices. Add functionality to an existing slice before you create a new one.

Each slice exposes interfaces that other slices can depend on, and owns the implementations of those interfaces. Select the concrete implementation at the application boundary, through dependency injection or composition. With Effect, this is a `Layer`.

### Slice structure

```text
Slice/
├── Domain.ts
├── Error.ts
├── utils.ts
├── persistence/
│   └── schema.ts
├── Services/
│   └── ...
└── Layer/
    └── ...
```

| Path | Contents |
|------|----------|
| `Domain.ts` | Entities, value objects, domain behavior, and domain invariants. |
| `Error.ts` | Domain errors, typed failures, and error helpers. |
| `utils.ts` | Pure helper functions for this slice only. No business logic. |
| `persistence/schema.ts` | Persistence models and schema definitions. Keep persistence details out of the domain. |
| `Services/` | Interfaces, service contracts, dependency tags, and ports only. No implementation. |
| `Layer/` | Implementations of the interfaces in `Services/`, such as repositories, HTTP clients, database adapters, and external integrations. All infrastructure code goes here. |

### Fixed rules

- Do not change the slice structure.
- Do not move responsibilities between folders.
- Do not merge the boundaries between folders.
- Keep domain logic independent of infrastructure. Infrastructure depends on the domain. The domain never depends on infrastructure.
