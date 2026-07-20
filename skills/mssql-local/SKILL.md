---
name: mssql-local
description: Access a local Microsoft SQL Server or Azure SQL-compatible database with the official sqlcmd CLI. Use when an agent needs to inspect schemas, query data, run T-SQL files, insert or update rows, delete data, or make DDL changes in a user-authorized local MSSQL database.
---

# MSSQL Local

Use `scripts/mssql.sh` as the single entry point. It keeps passwords out of process arguments, requires an explicit server and database, and separates reads, writes, and destructive operations.

## Prepare

1. Check that `sqlcmd` is installed:

   ```bash
   command -v sqlcmd
   ```

2. If it is missing or connection variables are not configured, read [references/setup.md](references/setup.md). Never install software or persist credentials without the user's authorization.
3. Require `SQLCMDSERVER` and `SQLCMDDBNAME`. Never silently default to `master` or another database.
4. Verify the target before other work:

   ```bash
   scripts/mssql.sh check
   ```

Stop if the returned server or database differs from the intended target.

## Inspect and read

Discover the schema instead of guessing names or types. Prefer catalog views such as `sys.tables`, `sys.columns`, `sys.indexes`, and `sys.foreign_keys`, or `INFORMATION_SCHEMA` when portability matters.

Pass SQL over standard input so it is not exposed in shell history or process arguments:

```bash
scripts/mssql.sh read <<'SQL'
SELECT TOP (20) id, status, created_at
FROM dbo.orders
ORDER BY created_at DESC;
SQL
```

Use `-` for stdin or pass one `.sql` file as the final argument. Add deterministic `ORDER BY` clauses and bounded `TOP` clauses for exploratory queries. Avoid `SELECT *` unless inspecting a very small known table.

## Write data

Treat the user's explicit request to insert or update known data as authorization for that scoped change. Before executing:

1. Inspect column types, constraints, triggers, and relevant unique or foreign keys.
2. Show or state the exact target and expected effect.
3. Make predicates precise. For updates, run the equivalent `SELECT` first and report the candidate row count.
4. Use a transaction, `SET XACT_ABORT ON`, and an affected-row assertion for non-trivial changes.
5. Enable the deliberate write gate only for the execution command:

```bash
MSSQL_ALLOW_WRITE=1 scripts/mssql.sh write <<'SQL'
SET XACT_ABORT ON;
BEGIN TRANSACTION;

UPDATE dbo.orders
SET status = N'cancelled'
WHERE id = 123 AND status = N'pending';

IF @@ROWCOUNT <> 1
    THROW 50001, 'Expected exactly one order to be updated', 1;

COMMIT TRANSACTION;
SQL
```

Read back the changed rows and report the observed result. Never interpolate untrusted values into T-SQL; use a parameterized application client when values originate outside the current trusted request.

## Delete data or change schema

Classify `DELETE`, `TRUNCATE`, `DROP`, potentially lossy `ALTER`, broad updates, permission changes, and database-level operations as destructive.

1. Resolve the exact server, database, schema, object, predicate, and dependencies.
2. Preview the same predicate with `SELECT` and `COUNT_BIG(*)`. For object changes, inspect dependencies and describe reversibility.
3. Obtain explicit user confirmation when the destructive scope was not already explicit in the current request. A general request to "clean up" is not enough authorization for a broad delete or drop.
4. Prefer a recoverable operation, transaction, backup, or archival approach. Note that some operations cannot be made safely reversible.
5. Add a row-count ceiling and fail closed. Do not use an unbounded delete merely because the current preview count is small.
6. Enable the destructive gate only for the reviewed command:

```bash
MSSQL_ALLOW_DESTRUCTIVE=1 scripts/mssql.sh destructive <<'SQL'
SET XACT_ABORT ON;
BEGIN TRANSACTION;

DECLARE @Affected bigint;
DELETE FROM dbo.sessions
WHERE expires_at < DATEADD(day, -30, SYSUTCDATETIME());
SET @Affected = @@ROWCOUNT;

IF @Affected > 1000
    THROW 50002, 'Delete exceeded the approved ceiling', 1;

COMMIT TRANSACTION;
SELECT @Affected AS deleted_rows;
SQL
```

Afterward, verify the resulting state and say what changed and whether it is recoverable.

## Handle failures

- Preserve the CLI error and relevant server/database/object context, but redact secrets and sensitive row data.
- Do not retry writes automatically when commit status is uncertain. Inspect state first.
- Treat deadlocks and transient connectivity failures as retryable only after confirming the operation is idempotent or did not commit.
- On constraint errors, inspect the named constraint and relevant metadata; do not disable constraints as a shortcut.
- For performance work, inspect the actual execution plan only when authorized and avoid running expensive diagnostics against a busy database.

