#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
test_dir=$(mktemp -d)
trap 'rm -rf -- "$test_dir"' EXIT

cat >"$test_dir/sqlcmd" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" >"$MSSQL_TEST_ARGS"
if [[ " $* " == *" -i /dev/stdin "* ]]; then
  cat >"$MSSQL_TEST_STDIN"
fi
EOF
chmod +x "$test_dir/sqlcmd"

export PATH="$test_dir:$PATH"
export SQLCMDSERVER='localhost,1433'
export SQLCMDDBNAME='app_db'
export SQLCMDUSER='app_agent'
export SQLCMDPASSWORD='not-printed'
export MSSQL_TEST_ARGS="$test_dir/args"
export MSSQL_TEST_STDIN="$test_dir/stdin"

env -u SQLCMDSERVER -u SQLCMDDBNAME PATH='/usr/bin:/bin' \
  "$script_dir/mssql.sh" --help >/dev/null

"$script_dir/mssql.sh" check >/dev/null
grep -Fx -- '-S' "$MSSQL_TEST_ARGS" >/dev/null
grep -Fx -- 'localhost,1433' "$MSSQL_TEST_ARGS" >/dev/null
grep -Fx -- '-d' "$MSSQL_TEST_ARGS" >/dev/null
grep -Fx -- 'app_db' "$MSSQL_TEST_ARGS" >/dev/null
if grep -F -- "$SQLCMDPASSWORD" "$MSSQL_TEST_ARGS" >/dev/null; then
  echo 'password leaked into sqlcmd arguments' >&2
  exit 1
fi

if "$script_dir/mssql.sh" write <<<'SELECT 1;' >/dev/null 2>&1; then
  echo 'write ran without MSSQL_ALLOW_WRITE=1' >&2
  exit 1
fi

MSSQL_ALLOW_WRITE=1 "$script_dir/mssql.sh" write <<<'UPDATE dbo.t SET value = 1;' >/dev/null
grep -Fx -- 'UPDATE dbo.t SET value = 1;' "$MSSQL_TEST_STDIN" >/dev/null

if "$script_dir/mssql.sh" destructive <<<'DELETE dbo.t;' >/dev/null 2>&1; then
  echo 'destructive operation ran without its gate' >&2
  exit 1
fi

MSSQL_ALLOW_DESTRUCTIVE=1 "$script_dir/mssql.sh" destructive <<<'DELETE dbo.t WHERE id = 1;' >/dev/null
grep -Fx -- 'DELETE dbo.t WHERE id = 1;' "$MSSQL_TEST_STDIN" >/dev/null

echo 'mssql-local wrapper tests passed'
