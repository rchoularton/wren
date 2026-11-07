#!/bin/bash
# Search the opt-in session logs by keyword.
#
# Usage: recall_context.sh <term> [term ...]
#   Terms are OR-combined, case-insensitive.
#   WREN_MEMORY_DIR overrides the auto-memory dir (default: derived from the
#   project path the same way Claude Code does).
#
# Output: one line per matching bullet, prefixed [date | session heading], so
# every hit is citable. Exit 0 on a hit, 1 on no match, 2 on bad usage.
# Reads only <memory>/context/sessions/*.md, never raw transcripts.

if [[ $# -eq 0 ]]; then
  echo "usage: recall_context.sh <term> [term ...]" >&2
  exit 2
fi

if [[ -n "${WREN_MEMORY_DIR:-}" ]]; then
  MEMORY_DIR="$WREN_MEMORY_DIR"
else
  MEMORY_DIR=$(python3 -c '
import os, re
from pathlib import Path
root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
slug = re.sub(r"[/.]", "-", str(Path(root).resolve()))
print(Path.home() / ".claude" / "projects" / slug / "memory")')
fi
SESSIONS_DIR="$MEMORY_DIR/context/sessions"

# OR pattern, lowercased (BSD awk has no IGNORECASE).
pattern=$(printf '%s|' "$@")
pattern=$(printf '%s' "${pattern%|}" | tr '[:upper:]' '[:lower:]')

found=0
shopt -s nullglob
files=("$SESSIONS_DIR"/*.md)
for ((i = ${#files[@]} - 1; i >= 0; i--)); do  # newest first
  f="${files[i]}"
  day=$(basename "$f" .md)
  hits=$(awk -v pat="$pattern" -v day="$day" '
    /^### / { heading = substr($0, 5) }
    tolower($0) ~ pat && /^- / { printf "[%s | %s] %s\n", day, heading, $0 }
  ' "$f")
  if [[ -n "$hits" ]]; then
    echo "=== $f ==="
    echo "$hits"
    echo
    found=1
  fi
done

if [[ $found -eq 0 ]]; then
  echo "nothing captured matches: $*"
  exit 1
fi
