#!/usr/bin/env python3
"""PreToolUse advisory for the sub-agent tool, `Agent` or `Task` (token-budget rule 6).

Built-in `Explore` / `general-purpose` sub-agents have no definition file, so
they inherit the caller's model, which on the main interactive loop is the
strong one. When one is launched without an explicit `model`, this hook emits a
NON-BLOCKING reminder to pin a cheaper tier. It never approves, denies, or
blocks: it omits `permissionDecision` and always exits 0, so normal permission
flow is untouched. If the input is unparseable, it stays silent.

Contract: PreToolUse hooks receive the tool call on stdin as JSON with
`tool_name`, `tool_input.subagent_type` and (optional) `tool_input.model`; a
non-blocking message is returned via hookSpecificOutput.additionalContext.
See https://code.claude.com/docs/en/hooks.md
"""
import json
import sys

INHERITING_BUILTINS = {"Explore", "general-purpose"}
# The sub-agent tool is `Task` in the CLI and `Agent` in the desktop app and
# newer harnesses; settings.json matches both, so the script must too.
SUBAGENT_TOOLS = {"Task", "Agent"}


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # never disrupt on bad/empty input

    if not isinstance(data, dict):
        return 0
    tool = data.get("tool_name")
    if not isinstance(tool, str) or tool not in SUBAGENT_TOOLS:
        return 0

    ti = data.get("tool_input")
    if not isinstance(ti, dict):
        return 0
    subagent = ti.get("subagent_type")
    model = ti.get("model")

    if isinstance(subagent, str) and subagent in INHERITING_BUILTINS and not model:
        msg = (
            f"[token-budget] '{subagent}' launched without an explicit model, so it "
            "inherits the caller's model (the strong one on the main loop). For "
            "search or file-reading, pass model:'sonnet'; for pure enumeration, "
            "model:'haiku'. Let it inherit the strong model only for genuine "
            "judgement fan-out. (.claude/rules/token-budget.md rule 6)"
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": msg,
            }
        }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail open on anything unexpected
