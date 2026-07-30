#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: resolve-handoff-path.sh --root | --history | --timeline | --checkpoint <sequence> <lifecycle> | --route <sequence> <from> <to> | <lifecycle>" >&2
  exit 2
}

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

if [[ "$#" -eq 1 && "$1" == "--root" ]]; then
  printf '%s\n' "$task_root"
  exit 0
fi

if [[ "$#" -eq 1 && "$1" == "--history" ]]; then
  printf '%s\n' "${task_root}/history"
  exit 0
fi

if [[ "$#" -eq 1 && "$1" == "--timeline" ]]; then
  printf '%s\n' "${task_root}/history/timeline.md"
  exit 0
fi

resolve_lifecycle_slug() {
  local lifecycle_name="${1//_/-}"
  local lifecycle_slug

  lifecycle_slug="$(slugify "$lifecycle_name")"
  case "$lifecycle_slug" in
    intake|context-gathering|analysis|replication|test-scope|planning|implementation|regression-scope|review|video-evidence|verification|delivery|awaiting-input|completed|cancelled)
      printf '%s' "$lifecycle_slug"
      ;;
    *)
      echo "unknown orchestrator lifecycle: $1" >&2
      exit 2
      ;;
  esac
}

resolve_sequence() {
  local sequence="$1"
  local sequence_name="$2"

  if [[ ! "$sequence" =~ ^[0-9]+$ ]] || (( 10#$sequence < 1 )); then
    echo "$sequence_name sequence must be a positive integer: $sequence" >&2
    exit 2
  fi

  printf '%06d' "$((10#$sequence))"
}

resolve_route_node_slug() {
  if [[ "$1" == "initial" ]]; then
    printf '%s' "initial"
    return
  fi

  resolve_lifecycle_slug "$1"
}

if [[ "$#" -eq 3 && "$1" == "--checkpoint" ]]; then
  padded_sequence="$(resolve_sequence "$2" "checkpoint")"
  lifecycle_slug="$(resolve_lifecycle_slug "$3")"
  printf '%s\n' "${task_root}/history/checkpoints/${padded_sequence}-${lifecycle_slug}"
  exit 0
fi

if [[ "$#" -eq 4 && "$1" == "--route" ]]; then
  padded_sequence="$(resolve_sequence "$2" "route")"
  from_slug="$(resolve_route_node_slug "$3")"
  to_slug="$(resolve_lifecycle_slug "$4")"
  printf '%s\n' "${task_root}/history/routes/${padded_sequence}-${from_slug}--${to_slug}"
  exit 0
fi

if [[ "$#" -ne 1 ]]; then
  usage
fi

lifecycle_slug="$(resolve_lifecycle_slug "$1")"

printf '%s\n' "${task_root}/${lifecycle_slug}"
