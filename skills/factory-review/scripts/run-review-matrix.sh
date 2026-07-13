#!/usr/bin/env bash

set -u

usage() {
  printf '%s\n' \
    'Usage: run-review-matrix.sh --repo PATH [--context-file FILE] [--scope TEXT] [--output-dir DIR] [--dry-run]' \
    '' \
    'Runs four independent review cells in parallel:' \
    '  codex  gpt-5.6-sol high      x bug-finder' \
    '  claude claude-fable-5[1m] high x bug-finder' \
    '  codex  gpt-5.6-sol high      x regression-reviewer' \
    '  claude claude-fable-5[1m] high x regression-reviewer'
}

repo=''
context_file=''
scope='Review the available context and the current branch, including staged, unstaged, and untracked changes.'
output_dir=''
dry_run='false'

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      repo=$2
      shift 2
      ;;
    --context-file)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      context_file=$2
      shift 2
      ;;
    --scope)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      scope=$2
      shift 2
      ;;
    --output-dir)
      [ "$#" -ge 2 ] || { usage >&2; exit 2; }
      output_dir=$2
      shift 2
      ;;
    --dry-run)
      dry_run='true'
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[ -n "$repo" ] || { printf '%s\n' '--repo is required' >&2; exit 2; }
[ -d "$repo" ] || { printf 'Repository does not exist: %s\n' "$repo" >&2; exit 2; }
repo=$(cd "$repo" && pwd)

if [ -n "$context_file" ]; then
  [ -f "$context_file" ] || { printf 'Context file does not exist: %s\n' "$context_file" >&2; exit 2; }
  context_file=$(cd "$(dirname "$context_file")" && pwd)/$(basename "$context_file")
fi

if [ -z "$output_dir" ]; then
  output_dir="${TMPDIR:-/tmp}/factory-review-$(date +%Y%m%d-%H%M%S)-$$"
fi
mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd)

codex_model=${CODEX_REVIEW_MODEL:-gpt-5.6-sol}
claude_model=${CLAUDE_REVIEW_MODEL:-claude-fable-5[1m]}

role_instructions() {
  case "$1" in
    bug-finder)
      printf '%s\n' 'Find concrete correctness defects, broken invariants, unsafe error paths, concurrency problems, data corruption, security-relevant bugs, and behavior that contradicts the supplied context. Prefer demonstrable failures over stylistic concerns.'
      ;;
    regression-reviewer)
      printf '%s\n' 'Find behavior that existing users, callers, integrations, data, or operations could lose. Check compatibility, edge cases, tests, migrations, performance, observability, rollback, and unchanged behavior outside the intended scope.'
      ;;
    *)
      printf 'Unknown role: %s\n' "$1" >&2
      return 2
      ;;
  esac
}

build_prompt() {
  model_label=$1
  role=$2

  printf '%s\n' \
    'You are one independent cell in a software review matrix.' \
    "Matrix cell: ${model_label} x ${role}" \
    '' \
    'Review only. Do not edit files, implement fixes, spawn or delegate to other agents, or communicate with other matrix cells.' \
    'Inspect repository instructions, relevant artifacts, git status, branch history, and diffs needed for the supplied scope.' \
    '' \
    'Review scope:' \
    "$scope" \
    '' \
    'Role:'
  role_instructions "$role"
  printf '%s\n' '' 'Human-supplied context:'
  if [ -n "$context_file" ]; then
    sed -n '1,4000p' "$context_file"
  else
    printf '%s\n' 'No additional context file was supplied. Use the review scope and repository state.'
  fi
  printf '%s\n' \
    '' \
    'Return findings only when supported by evidence. For each finding include:' \
    '- severity: P0, P1, P2, or P3' \
    '- concise title' \
    '- precise file:line or artifact location' \
    '- evidence and triggering conditions' \
    '- user or system impact' \
    '- smallest safe recommendation' \
    '- confidence: high, medium, or low' \
    '' \
    'If there are no findings, state that clearly and list what you inspected and the remaining uncertainty.' \
    'Do not number findings; the orchestrator assigns merged report identifiers.'
}

if [ "$dry_run" = 'true' ]; then
  printf 'Output directory: %s\n' "$output_dir"
  printf 'Codex model: %s (high)\n' "$codex_model"
  printf 'Claude model: %s (high)\n' "$claude_model"
  printf '%s\n' \
    'Cells:' \
    '  codex-bug-finder' \
    '  claude-bug-finder' \
    '  codex-regression-reviewer' \
    '  claude-regression-reviewer'
  exit 0
fi

write_preflight_failure() {
  reason=$1
  manifest="$output_dir/manifest.md"
  {
    printf '%s\n' '# Factory Review Matrix'
    printf '\n- Repository: `%s`\n' "$repo"
    printf -- '- Scope: %s\n' "$scope"
    printf -- '- Status: `not-started`\n'
    printf -- '- Reason: %s\n\n' "$reason"
    printf '%s\n' \
      '| Cell | Status |' \
      '|---|---|' \
      '| codex-bug-finder | unavailable |' \
      '| claude-bug-finder | unavailable |' \
      '| codex-regression-reviewer | unavailable |' \
      '| claude-regression-reviewer | unavailable |'
  } >"$manifest"
  printf 'Manifest: %s\n' "$manifest" >&2
}

missing='false'
missing_clis=''
for cli in codex claude; do
  if ! command -v "$cli" >/dev/null 2>&1; then
    printf 'Required CLI is unavailable: %s\n' "$cli" >&2
    missing='true'
    missing_clis="${missing_clis}${missing_clis:+, }${cli}"
  fi
done

if [ "$missing" = 'true' ]; then
  write_preflight_failure "Required CLI unavailable: ${missing_clis}"
  printf '%s\n' 'Matrix not started; all four cells are required.' >&2
  exit 3
fi

if ! codex --version >/dev/null 2>&1; then
  write_preflight_failure 'Codex CLI version preflight failed.'
  printf '%s\n' 'Codex CLI preflight failed; matrix not started.' >&2
  exit 3
fi

if ! claude --version >/dev/null 2>&1; then
  write_preflight_failure 'Claude CLI version preflight failed.'
  printf '%s\n' 'Claude CLI preflight failed; matrix not started.' >&2
  exit 3
fi

if ! codex login status >/dev/null 2>&1; then
  write_preflight_failure 'Codex CLI authentication preflight failed.'
  printf '%s\n' 'Codex CLI is not authenticated; matrix not started.' >&2
  exit 3
fi

if ! claude auth status >/dev/null 2>&1; then
  write_preflight_failure 'Claude CLI authentication preflight failed.'
  printf '%s\n' 'Claude CLI is not authenticated; matrix not started.' >&2
  exit 3
fi

run_codex() {
  role=$1
  output=$2
  log=$3
  build_prompt 'Codex 5.6 Sol High' "$role" |
    codex exec \
      --ephemeral \
      --sandbox read-only \
      -C "$repo" \
      -m "$codex_model" \
      -c 'model_reasoning_effort="high"' \
      -o "$output" \
      - >"$log" 2>&1
}

run_claude() {
  role=$1
  output=$2
  log=$3
  (
    cd "$repo" || exit 2
    build_prompt 'Claude Fable 5 High' "$role" |
      claude \
        -p \
        --model "$claude_model" \
        --effort high \
        --permission-mode plan \
        --tools 'Read,Grep,Glob,Bash' \
        --output-format text \
        --no-session-persistence \
        >"$output" 2>"$log"
  )
}

labels=(
  'codex-bug-finder'
  'claude-bug-finder'
  'codex-regression-reviewer'
  'claude-regression-reviewer'
)
outputs=(
  "$output_dir/codex-bug-finder.md"
  "$output_dir/claude-bug-finder.md"
  "$output_dir/codex-regression-reviewer.md"
  "$output_dir/claude-regression-reviewer.md"
)
logs=(
  "$output_dir/codex-bug-finder.log"
  "$output_dir/claude-bug-finder.log"
  "$output_dir/codex-regression-reviewer.log"
  "$output_dir/claude-regression-reviewer.log"
)
pids=()

run_codex 'bug-finder' "${outputs[0]}" "${logs[0]}" &
pids+=("$!")
run_claude 'bug-finder' "${outputs[1]}" "${logs[1]}" &
pids+=("$!")
run_codex 'regression-reviewer' "${outputs[2]}" "${logs[2]}" &
pids+=("$!")
run_claude 'regression-reviewer' "${outputs[3]}" "${logs[3]}" &
pids+=("$!")

statuses=()
failures=0
i=0
while [ "$i" -lt "${#pids[@]}" ]; do
  if wait "${pids[$i]}" && [ -s "${outputs[$i]}" ]; then
    statuses+=("completed")
  else
    statuses+=("failed")
    failures=$((failures + 1))
  fi
  i=$((i + 1))
done

manifest="$output_dir/manifest.md"
{
  printf '%s\n' '# Factory Review Matrix'
  printf '\n- Repository: `%s`\n' "$repo"
  printf -- '- Scope: %s\n' "$scope"
  printf -- '- Codex model: `%s` at high effort\n' "$codex_model"
  printf -- '- Claude model: `%s` at high effort\n\n' "$claude_model"
  printf '%s\n' '| Cell | Status | Output | Log |' '|---|---|---|---|'
  i=0
  while [ "$i" -lt "${#labels[@]}" ]; do
    printf '| %s | %s | `%s` | `%s` |\n' "${labels[$i]}" "${statuses[$i]}" "${outputs[$i]}" "${logs[$i]}"
    i=$((i + 1))
  done
} >"$manifest"

printf 'Review matrix artifacts: %s\n' "$output_dir"
printf 'Manifest: %s\n' "$manifest"

if [ "$failures" -gt 0 ]; then
  printf '%s cell(s) failed; report the matrix as incomplete.\n' "$failures" >&2
  exit 4
fi
