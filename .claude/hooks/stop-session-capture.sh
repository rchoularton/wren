#!/bin/bash
# Stop hook: opt-in capture of the session's last exchange into a dated log
# (<auto-memory dir>/context/sessions/YYYY-MM-DD.md).
#
# OFF unless `tiers.session_capture: true` in research-config.yml. Fire-and-
# forget: dispatches a detached helper and exits at once, so session end is
# never blocked. The helper makes one headless `claude -p --model haiku` call.
#
# Re-trigger guard: WREN_CAPTURE_HOOK is set inside the helper's own claude
# call (belt); the helper also runs claude from $HOME so this project's hooks
# never load (braces).

if [[ -n "${WREN_CAPTURE_HOOK:-}" ]]; then
  exit 0
fi

payload=$(cat)

# Toggle check: line-scan of the `tiers:` block, no pyyaml. Missing file = off.
enabled=$(python3 - <<'PY' 2>/dev/null
import os, re
try:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    inside = False
    for line in open(os.path.join(root, "research-config.yml"), encoding="utf-8"):
        if re.match(r"^tiers\s*:", line):
            inside = True
            continue
        if inside:
            if line.strip() and not line.startswith((" ", "\t", "#")):
                break
            m = re.match(r"^\s+session_capture\s*:\s*(\S+)", line)
            if m:
                print("yes" if m.group(1).strip("\"'").lower() == "true" else "no")
                break
except Exception:
    pass
PY
)
if [[ "$enabled" != "yes" ]]; then
  exit 0
fi

read -r transcript_path session_id < <(echo "$payload" | python3 -c '
import json,sys
d=json.load(sys.stdin)
print((d.get("transcript_path","") or "-"), (d.get("session_id","") or "-"))' 2>/dev/null)

if [[ -z "$transcript_path" || "$transcript_path" == "-" || ! -f "$transcript_path" ]]; then
  exit 0
fi
[[ "$session_id" == "-" ]] && session_id=""

nohup python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/hooks/capture_session.py" \
  "$transcript_path" "$session_id" >/dev/null 2>&1 &
disown

exit 0
