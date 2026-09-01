#!/usr/bin/env bash
set -euo pipefail

slugify() {
  local value="${1//\//--}"
  value="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g; s/^[.-]+//; s/[.-]+$//')"
  printf '%s' "${value:-unknown}"
}

workspace_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
project_slug="$(slugify "$(basename "$workspace_root")")"
branch_name="$(git -C "$workspace_root" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
if [[ -z "$branch_name" ]]; then
  short_sha="$(git -C "$workspace_root" rev-parse --short HEAD 2>/dev/null || true)"
  branch_name="${short_sha:+detached-$short_sha}"
  branch_name="${branch_name:-no-branch}"
fi

printf '%s\n' "${HOME}/.agents-db/${project_slug}/$(slugify "$branch_name")"
