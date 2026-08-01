#!/bin/bash
# PreToolUse hook for Write|Edit|MultiEdit.
#
# Defense-in-depth "never overwrite" guard. Blocks writes whose path starts
# with any prefix listed in .claude/hooks/protected_paths.txt (one per line),
# which the setup renderer generates from research-config.yml
# (paths.protected_write_paths). If that file is absent or empty, nothing is
# blocked. settings.local.json deny patterns remain the primary gate; this is
# the second belt plus an audit trail.
#
# Decision: "block" on a match, "approve" otherwise. Never errors out.

set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
LOG_DIR="$ROOT/outputs/_logs"
LOG="$LOG_DIR/pre_write_guard.log"
PROTECTED_FILE="$ROOT/.claude/hooks/protected_paths.txt"
mkdir -p "$LOG_DIR" 2>/dev/null || true

payload=$(cat)

target=$(echo "$payload" | python3 -c '
import json, sys
try:
  data = json.load(sys.stdin)
  ti = data.get("tool_input", {}) or {}
  print(ti.get("file_path") or ti.get("path") or "")
except Exception:
  print("")
' 2>/dev/null || true)

ts=$(date "+%Y-%m-%d %H:%M:%S")

if [[ -z "$target" ]]; then
  echo '{"decision":"approve"}'
  exit 0
fi

if [[ -f "$PROTECTED_FILE" ]]; then
  # Expand ~ in the target for comparison
  expanded_target="${target/#\~/$HOME}"
  while IFS= read -r prefix; do
    [[ -z "$prefix" || "$prefix" == \#* ]] && continue
    expanded_prefix="${prefix/#\~/$HOME}"
    if [[ "$expanded_target" == "$expanded_prefix"* ]]; then
      echo "[$ts] BLOCKED $target (matched $prefix)" >> "$LOG"
      cat <<EOF
{
  "decision": "block",
  "reason": "Path is protected by your research-config.yml (paths.protected_write_paths). To make major changes, use the paper build/extract workflow or copy to a project location first."
}
EOF
      exit 0
    fi
  done < "$PROTECTED_FILE"
fi

echo '{"decision":"approve"}'
