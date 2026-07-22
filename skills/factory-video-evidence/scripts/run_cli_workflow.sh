#!/usr/bin/env bash

set -Eeuo pipefail

usage() {
  echo "Usage: $0 --session NAME --url URL --script FILE [--state FILE] [--video FILE] [--test-case TEXT]" >&2
}

session_name=""
start_url=""
workflow_script=""
state_path=""
video_path=""
test_case=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session | --url | --script | --state | --video | --test-case)
      if [[ $# -lt 2 || -z "$2" ]]; then
        usage
        exit 2
      fi
      option="$1"
      value="$2"
      shift 2
      case "$option" in
        --session) session_name="$value" ;;
        --url) start_url="$value" ;;
        --script) workflow_script="$value" ;;
        --state) state_path="$value" ;;
        --video) video_path="$value" ;;
        --test-case) test_case="$value" ;;
      esac
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$session_name" || -z "$start_url" || -z "$workflow_script" ]]; then
  usage
  exit 2
fi

if ! command -v playwright-cli >/dev/null 2>&1; then
  echo "playwright-cli is not available on PATH" >&2
  exit 127
fi

if [[ ! -f "$workflow_script" ]]; then
  echo "Workflow script not found: $workflow_script" >&2
  exit 2
fi

workflow_script="$(realpath "$workflow_script")"
if [[ -n "$state_path" ]]; then
  if [[ ! -f "$state_path" ]]; then
    echo "Auth state not found: $state_path" >&2
    exit 2
  fi
  state_path="$(realpath "$state_path")"
fi
if [[ -n "$video_path" ]]; then
  video_path="$(realpath --canonicalize-missing "$video_path")"
  if [[ -e "$video_path" ]]; then
    echo "Refusing to overwrite existing video: $video_path" >&2
    exit 2
  fi
  if [[ ! -d "$(dirname "$video_path")" ]]; then
    echo "Video directory does not exist: $(dirname "$video_path")" >&2
    exit 2
  fi
fi

session_opened=false
video_started=false
test_case_script=""

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  set +e

  if [[ "$video_started" == true ]]; then
    playwright-cli -s="$session_name" video-stop >/dev/null 2>&1
  fi
  if [[ "$session_opened" == true ]]; then
    playwright-cli -s="$session_name" close >/dev/null 2>&1
  fi
  if [[ -n "$test_case_script" ]]; then
    rm -f -- "$test_case_script"
  fi
  exit "$exit_code"
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

session_opened=true
playwright-cli -s="$session_name" open about:blank

if [[ -n "$state_path" ]]; then
  playwright-cli -s="$session_name" state-load "$state_path"
fi

playwright-cli -s="$session_name" goto "$start_url"

if [[ -n "$test_case" ]]; then
  test_case_script="$(mktemp "${TMPDIR:-/tmp}/factory-video-test-case.XXXXXX.js")"
  test_case_base64="$(printf '%s' "$test_case" | base64 | tr -d '\n')"
  sed "s|__FACTORY_TEST_CASE_BASE64__|$test_case_base64|" \
    "$(dirname "$0")/inject_video_test_case.js" > "$test_case_script"
  playwright-cli -s="$session_name" run-code --filename="$test_case_script"
fi

if [[ -n "$video_path" ]]; then
  playwright-cli -s="$session_name" video-start "$video_path"
  video_started=true
fi

playwright-cli -s="$session_name" run-code --filename="$workflow_script"

if [[ "$video_started" == true ]]; then
  playwright-cli -s="$session_name" video-stop
  video_started=false
fi

playwright-cli -s="$session_name" close
session_opened=false
