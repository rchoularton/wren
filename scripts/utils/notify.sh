#!/usr/bin/env bash
# Ambient notifications for shell scripts.
#
# Usage:
#   source scripts/utils/notify.sh
#   notify START "My Script"
#   # ... work ...
#   notify DONE "My Script" "" "$SECONDS"   # SECONDS is a bash built-in
#
# Or run as a wrapper:
#   scripts/utils/notify.sh wrap "My Script" -- long_running_command --flags
#
# Events: START, DONE, WARN, ERROR. Appends to RUNNING.md in the project root.
# Desktop notifications use terminal-notifier if present (macOS); otherwise the
# RUNNING.md log still records everything. Group name from NOTIFY_GROUP env
# (default "research-assistant").

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNNING_MD="$PROJECT_ROOT/RUNNING.md"
TERMINAL_NOTIFIER="$(command -v terminal-notifier || echo /opt/homebrew/bin/terminal-notifier)"
NOTIFY_GROUP="${NOTIFY_GROUP:-research-assistant}"

_fmt_duration() {
  local s=$1
  if (( s < 60 )); then
    printf "%ss" "$s"
  elif (( s < 3600 )); then
    printf "%dm%02ds" $((s/60)) $((s%60))
  else
    printf "%dh%02dm" $((s/3600)) $(((s%3600)/60))
  fi
}

notify() {
  local event="$1"
  local script="${2:-script}"
  local detail="${3:-}"
  local duration="${4:-}"
  local ts sound prefix line
  ts="$(date '+%Y-%m-%d %H:%M:%S')"

  case "$event" in
    START) prefix="▶"; sound="" ;;
    DONE)  prefix="✓"; sound="Glass" ;;
    WARN)  prefix="⚠"; sound="" ;;
    ERROR) prefix="✗"; sound="Basso" ;;
    *)     prefix="·"; sound="" ;;
  esac

  line="- $prefix \`$ts\` **$event** $script"
  if [[ -n "$duration" ]]; then
    line="$line ($(_fmt_duration "$duration"))"
  fi
  if [[ -n "$detail" ]]; then
    line="$line — $detail"
  fi

  if [[ ! -f "$RUNNING_MD" ]]; then
    printf "# Running Scripts\n\nLive log of notification events. Git-ignored.\n\n" > "$RUNNING_MD"
  fi
  echo "$line" >> "$RUNNING_MD"

  if [[ -x "$TERMINAL_NOTIFIER" ]]; then
    local args=(-title "$event: $script" -message "${detail:-$script}" -group "$NOTIFY_GROUP")
    [[ -n "$sound" ]] && args+=(-sound "$sound")
    "$TERMINAL_NOTIFIER" "${args[@]}" >/dev/null 2>&1 || true
  fi
}

# Wrapper mode: scripts/utils/notify.sh wrap "Script Name" -- cmd args...
if [[ "${1:-}" == "wrap" ]]; then
  shift
  script_name="${1:-wrapped command}"; shift
  [[ "${1:-}" == "--" ]] && shift
  notify START "$script_name"
  t0=$SECONDS
  if "$@"; then
    notify DONE "$script_name" "" $((SECONDS - t0))
  else
    rc=$?
    notify ERROR "$script_name" "exit code $rc" $((SECONDS - t0))
    exit $rc
  fi
fi
