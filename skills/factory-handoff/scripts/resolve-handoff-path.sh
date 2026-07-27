#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: resolve-handoff-path.sh --root | <lifecycle>" >&2
  exit 2
}

if [[ "$#" -ne 1 ]]; then
  usage
fi

slugify() {
  local raw_value="$1"
  local slash_safe="${raw_value//\//--}"
  local slug

  slug="$(printf '%s' "$slash_safe" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9._-]+/-/g; s/^[.-]+//; s/[.-]+$//')"

  if [[ -z "$slug" ]]; then
    printf '%s' "unknown"
    return
  fi

  printf '%s' "$slug"
}

workspace_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
project_slug="$(slugify "$(basename "$workspace_root")")"

branch_name="$(git -C "$workspace_root" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
if [[ -z "$branch_name" ]]; then
  short_sha="$(git -C "$workspace_root" rev-parse --short HEAD 2>/dev/null || true)"
  if [[ -n "$short_sha" ]]; then
    branch_name="detached-$short_sha"
  else
    branch_name="no-branch"
  fi
fi

branch_slug="$(slugify "$branch_name")"
task_root="${HOME}/.agents-db/${project_slug}/${branch_slug}"

if [[ "$1" == "--root" ]]; then
  printf '%s\n' "$task_root"
  exit 0
fi

lifecycle_name="${1//_/-}"
lifecycle_slug="$(slugify "$lifecycle_name")"
case "$lifecycle_slug" in
  intake|context-gathering|analysis|planning|implementation|review|verification|delivery|awaiting-input|completed|cancelled)
    ;;
  *)
    echo "unknown orchestrator lifecycle: $1" >&2
    exit 2
    ;;
esac

printf '%s\n' "${task_root}/${lifecycle_slug}"
