#!/usr/bin/env python3
"""Allowlist guard for unattended runs (WREN_UNATTENDED set). Fails closed.

Active when WREN_UNATTENDED is anything other than empty, 0, false or no (any case). Inactive: exits 0
and prints nothing. Active: reads the PreToolUse event on stdin and either prints nothing (allowed) or
denies the call. A deny is emitted as hookSpecificOutput.permissionDecision "deny" with a reason and
the process exits 2 with the reason on stderr, so it blocks regardless of allow rules.

Allowed while active:
  Bash  - exactly: `date +%F`; the duplicate scan, queue builder and queue `status` for outputs/librarian
          with a YYYY-MM-DD date; no shell metacharacters.
  Write - only <project>/outputs/librarian/{cataloguer,scout}_<date>.{md,proposals.json} and report_<date>.md.
  mcp__ - only the read-only Zotero tools the librarian agents use, and the Gmail create-draft tool.
Everything else this hook sees (Edit, MultiEdit, NotebookEdit, other mcp__ tools, other commands) is denied.
"""
import json
import os
import re
import sys

D = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
BASH_PATTERNS = [
    re.compile(r"date \+%F"),
    re.compile(rf"npm run zotero:duplicates -- --out outputs/librarian/duplicates_({D})\.json --proposals outputs/librarian/duplicates_\1\.proposals\.json( --limit [0-9]+)?( --no-fuzzy)?"),
    re.compile(rf"npm run zotero:build-queue -- --date {D}"),
    re.compile(rf"npm run zotero:queue -- status outputs/librarian/approval_queue_{D}\.json"),
]
FORBIDDEN_CHARS = set(";&|$`><(){}\\\n\r")
WRITE_NAMES = re.compile(rf"(?:(?:cataloguer|scout)_{D}\.(?:md|proposals\.json)|report_{D}\.md)")
ALLOWED_MCP = {
    "mcp__zotero__zotero_search_items",
    "mcp__zotero__zotero_get_item_metadata",
    "mcp__zotero__zotero_get_recent",
    "mcp__zotero__zotero_get_tags",
    "mcp__zotero__zotero_get_collections",
    "mcp__zotero__zotero_search_collections",
    "mcp__claude_ai_Gmail__create_draft",
}


def is_active(env=os.environ):
    v = env.get("WREN_UNATTENDED")
    if v is None:
        return False
    return v.strip().lower() not in ("", "0", "false", "no")


def deny(reason):
    sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}))
    sys.stderr.write(reason + "\n")
    sys.exit(2)


def check_bash(command):
    cmd = command.strip()
    if any(c in FORBIDDEN_CHARS for c in cmd):
        return "unattended run: command not on the allowlist"
    if any(p.fullmatch(cmd) for p in BASH_PATTERNS):
        return None
    return "unattended run: command not on the allowlist"


def check_write(path_value, project):
    if not isinstance(path_value, str) or not path_value:
        return "unattended run: write path missing"
    p = path_value if os.path.isabs(path_value) else os.path.join(project, path_value)
    real = os.path.realpath(p)  # resolves symlinks and ".."; works for a file that does not exist yet
    libdir = os.path.realpath(os.path.join(project, "outputs", "librarian"))
    if os.path.dirname(real) != libdir or not WRITE_NAMES.fullmatch(os.path.basename(real)):
        return "unattended run: write not allowed outside the librarian report and proposals files"
    return None


def main():
    if not is_active():
        return
    try:
        event = json.loads(sys.stdin.read())
        if not isinstance(event, dict):
            raise ValueError("event is not an object")
        tool = event.get("tool_name")
        tool_input = event.get("tool_input") or {}
        if not isinstance(tool, str) or not isinstance(tool_input, dict):
            raise ValueError("bad tool fields")
    except Exception:
        deny("unattended run: unreadable hook input")
    project = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()
    if tool == "Bash":
        reason = check_bash(tool_input.get("command") if isinstance(tool_input.get("command"), str) else "\n")
    elif tool == "Write":
        reason = check_write(tool_input.get("file_path"), project)
    elif tool in ("Edit", "MultiEdit", "NotebookEdit"):
        reason = f"unattended run: {tool} is not allowed"
    elif tool.startswith("mcp__"):
        reason = None if tool in ALLOWED_MCP else "unattended run: tool not on the allowlist"
    else:
        reason = None  # tools this hook is not registered for are not its business
    if reason:
        deny(reason)


if __name__ == "__main__":
    main()
