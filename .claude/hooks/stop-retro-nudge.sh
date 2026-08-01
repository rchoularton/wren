#!/bin/bash
# Stop hook: nudge /retro for substantive sessions, stay silent otherwise.
# NEVER blocks — always approves session end.
#
# "Substantive" heuristic: transcript has > 20 events (JSONL lines).
# A 3-4 turn session is typically ~12-16 events; work sessions run much longer.

THRESHOLD=20

payload=$(cat)
transcript_path=$(echo "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("transcript_path",""))' 2>/dev/null)

event_count=0
if [[ -n "$transcript_path" && -f "$transcript_path" ]]; then
  event_count=$(wc -l < "$transcript_path" 2>/dev/null || echo 0)
fi

if (( event_count < THRESHOLD )); then
  echo '{"decision":"approve"}'
  exit 0
fi

cat <<'EOF'
{
  "decision": "approve",
  "systemMessage": "Session ending. If this session produced learnings worth remembering (process improvements, research insights, or system feedback), offer to run /retro quick before closing. If the session was trivial or administrative, just confirm done."
}
EOF
