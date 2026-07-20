# Install and configure sqlcmd

Use Microsoft's Go-based `sqlcmd`, the current cross-platform CLI for SQL Server, Azure SQL Database, and Azure Synapse. Do not use the unmaintained `mssql-cli` project. The older ODBC `sqlcmd` remains supported, but the Go implementation is the preferred modern option.

Official installation instructions:

- <https://learn.microsoft.com/sql/tools/sqlcmd/sqlcmd-download-install>
- <https://github.com/microsoft/go-sqlcmd>

Typical package-manager commands are:

```text
Windows: winget install sqlcmd
macOS:   brew install sqlcmd
Linux:   brew install sqlcmd
```

Microsoft also publishes `.deb`, `.rpm`, and tar archives for Linux. Follow the official page for the current repository and package commands rather than copying version-specific commands into this skill.

## Configure a connection

Export connection values in the invoking environment. Do not write secrets into this skill, a repository, shell history, command arguments, or logs.

For SQL authentication:

```bash
export SQLCMDSERVER='localhost,1433'
export SQLCMDDBNAME='my_database'
export SQLCMDUSER='agent_user'
export SQLCMDPASSWORD='use-a-secret-manager-or-private-session-value'
```

For integrated authentication, omit `SQLCMDUSER` and `SQLCMDPASSWORD`, then set:

```bash
export MSSQL_USE_INTEGRATED_AUTH=1
```

For Microsoft Entra authentication, omit the other authentication modes, authenticate with the supported local credential provider, then set:

```bash
export MSSQL_USE_AZURE_AD=1
```

For a local development certificate only, `MSSQL_TRUST_SERVER_CERTIFICATE=1` adds `-C`. Do not normalize bypassing certificate validation for remote or production systems.

Use a dedicated least-privilege database principal. Grant only the schemas and actions needed; do not use `sa`, `sysadmin`, or `db_owner` for routine agent work. Prefer separate read-only and writer principals when practical.

Optional official `sqlcmd` environment variables include `SQLCMDLOGINTIMEOUT` and `SQLCMDSTATTIMEOUT`. Set finite timeouts appropriate to the operation, especially for unattended work.
