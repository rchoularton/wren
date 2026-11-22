#!/bin/bash
# PreToolUse hook (Bash, Write|Edit|MultiEdit|NotebookEdit, mcp__.*): the enforced boundary of an
# unattended run. Does nothing unless WREN_UNATTENDED is set (the scheduled /librarian-team job
# exports it); the Python guard then decides each call and denies anything off its allowlist.
[ -z "${WREN_UNATTENDED:-}" ] && exit 0
exec python3 "$(dirname "$0")/unattended_guard.py"
