#!/bin/bash
# PreToolUse hook (Bash, Write|Edit|MultiEdit|NotebookEdit, Read|Grep|Glob, WebFetch|WebSearch, mcp__.*):
# the enforced boundary of an unattended run. Does nothing unless WREN_UNATTENDED is set (the scheduled
# /librarian-team job exports it). The Python guard then decides each call.
#
# Fail closed: Claude Code treats any non-zero exit other than 2 as a non-blocking error and lets the
# call proceed, so every outcome of the guard other than exit 0 (allow) or exit 2 (deny) is turned into
# a deny here (missing python3, a crash, exit 1, exit 127).
# Inactive values (same rule as the guard): empty, 0, false, no (any case, whitespace ignored).
_v="${WREN_UNATTENDED:-}"
_v="${_v//[[:space:]]/}"
shopt -s nocasematch
case "$_v" in ""|0|false|no) exit 0 ;; esac
shopt -u nocasematch
payload=$(</dev/stdin)
out=$(printf '%s' "$payload" | python3 "${0%/*}/unattended_guard.py")
rc=$?
if [ "$rc" -eq 0 ]; then
  [ -n "$out" ] && printf '%s\n' "$out"
  exit 0
fi
if [ "$rc" -eq 2 ] && [ -n "$out" ]; then
  printf '%s\n' "$out"
  exit 2
fi
printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"unattended guard error"}}'
echo "unattended guard error" >&2
exit 2
