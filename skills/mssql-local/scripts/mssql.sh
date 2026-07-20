#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: mssql.sh check
       mssql.sh read [SQL_FILE|-]
       MSSQL_ALLOW_WRITE=1 mssql.sh write [SQL_FILE|-]
       MSSQL_ALLOW_DESTRUCTIVE=1 mssql.sh destructive [SQL_FILE|-]

Required: SQLCMDSERVER, SQLCMDDBNAME, and sqlcmd on PATH.
Authentication: set SQLCMDUSER and SQLCMDPASSWORD for SQL authentication,
or set MSSQL_USE_AZURE_AD=1 or MSSQL_USE_INTEGRATED_AUTH=1.
EOF
}

fail() {
  printf 'mssql-local: %s\n' "$1" >&2
  exit 2
}

[[ $# -ge 1 ]] || { usage >&2; exit 2; }

action=$1
shift

case "$action" in
  help|-h|--help)
    usage
    exit 0
    ;;
esac

command -v sqlcmd >/dev/null 2>&1 || fail "sqlcmd is not installed or not on PATH; see references/setup.md"
[[ -n "${SQLCMDSERVER:-}" ]] || fail "SQLCMDSERVER must name the intended server"
[[ -n "${SQLCMDDBNAME:-}" ]] || fail "SQLCMDDBNAME must name the intended database"

auth_mode_count=0
[[ -n "${SQLCMDUSER:-}" ]] && auth_mode_count=$((auth_mode_count + 1))
[[ "${MSSQL_USE_AZURE_AD:-0}" == "1" ]] && auth_mode_count=$((auth_mode_count + 1))
[[ "${MSSQL_USE_INTEGRATED_AUTH:-0}" == "1" ]] && auth_mode_count=$((auth_mode_count + 1))
[[ $auth_mode_count -le 1 ]] || fail "configure exactly one authentication mode"

sqlcmd_args=(-S "$SQLCMDSERVER" -d "$SQLCMDDBNAME" -b -V 16 -r 1)

if [[ -n "${SQLCMDUSER:-}" ]]; then
  sqlcmd_args+=(-U "$SQLCMDUSER")
elif [[ "${MSSQL_USE_AZURE_AD:-0}" == "1" ]]; then
  sqlcmd_args+=(-G)
elif [[ "${MSSQL_USE_INTEGRATED_AUTH:-0}" == "1" ]]; then
  sqlcmd_args+=(-E)
fi

if [[ "${MSSQL_TRUST_SERVER_CERTIFICATE:-0}" == "1" ]]; then
  sqlcmd_args+=(-C)
fi

printf 'mssql-local: target server=%q database=%q action=%s\n' \
  "$SQLCMDSERVER" "$SQLCMDDBNAME" "$action" >&2

case "$action" in
  check)
    [[ $# -eq 0 ]] || fail "check does not accept a SQL file"
    sqlcmd "${sqlcmd_args[@]}" -Q \
      "SET NOCOUNT ON; SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, ORIGINAL_LOGIN() AS login_name;"
    ;;
  read)
    ;;
  write)
    [[ "${MSSQL_ALLOW_WRITE:-0}" == "1" ]] || \
      fail "write blocked; set MSSQL_ALLOW_WRITE=1 after reviewing the target and SQL"
    ;;
  destructive)
    [[ "${MSSQL_ALLOW_DESTRUCTIVE:-0}" == "1" ]] || \
      fail "destructive operation blocked; set MSSQL_ALLOW_DESTRUCTIVE=1 after scope review and authorization"
    ;;
  *)
    usage >&2
    fail "unknown action: $action"
    ;;
esac

[[ "$action" != "check" ]] || exit 0
[[ $# -le 1 ]] || fail "$action accepts at most one SQL file"

sql_file=${1:--}
if [[ "$sql_file" == "-" ]]; then
  sqlcmd "${sqlcmd_args[@]}" -i /dev/stdin
else
  [[ -f "$sql_file" ]] || fail "SQL file not found: $sql_file"
  sqlcmd "${sqlcmd_args[@]}" -i "$sql_file"
fi
