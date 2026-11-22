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
  Read/Grep/Glob - only inside the project, never secret files (.env, .env.*, .mcp.json, settings.local.json,
          .npmrc, anything under .git/); a Grep/Glob filename filter aimed at those names is denied too.
  WebFetch - https only, no userinfo in the URL. WebSearch is allowed.
For every tool it sees, the call is also denied when its input contains a secret value (a *KEY/TOKEN/SECRET/PASSWORD
value of at least 8 characters from <project>/.env or this process's environment), raw, URL-encoded or base64.
That blocks the literal forms, not every possible encoding.
Everything else this hook sees (Edit, MultiEdit, NotebookEdit, other mcp__ tools, other commands) is denied.
"""
import base64
import json
import os
import re
import sys
import urllib.parse

D = r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
BASH_PATTERNS = [
    re.compile(r"date \+%F"),
    re.compile(rf"npm run zotero:duplicates -- --out outputs/librarian/duplicates_({D})\.json --proposals outputs/librarian/duplicates_\1\.proposals\.json( --limit [0-9]+)?( --no-fuzzy)?"),
    re.compile(rf"npm run zotero:build-queue -- --date {D}"),
    re.compile(rf"npm run zotero:queue -- status outputs/librarian/approval_queue_{D}\.json"),
]
STATUS_RE = re.compile(r"npm run zotero:queue -- status (\S+)")
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


def check_bash(command, project):
    cmd = command.strip()
    if any(c in FORBIDDEN_CHARS for c in cmd):
        return "unattended run: command not on the allowlist"
    if any(p.fullmatch(cmd) for p in BASH_PATTERNS):
        return None
    m = STATUS_RE.fullmatch(cmd)
    if m and os.path.isabs(m.group(1)):
        real = os.path.realpath(m.group(1))
        libdir = os.path.realpath(os.path.join(project, "outputs", "librarian"))
        if os.path.dirname(real) == libdir and re.fullmatch(rf"approval_queue_{D}\.json", os.path.basename(real)):
            return None
    return "unattended run: command not on the allowlist"


SECRET_BASENAMES = {".mcp.json", "settings.local.json", ".npmrc"}
SENSITIVE_PATTERN = re.compile(r"(\.env(?!\.example)|\.mcp\.json|settings\.local\.json|\.npmrc|\.git(/|$))")


def sensitive_name(path):
    parts = path.replace("\\", "/").split("/")
    if ".git" in parts:
        return True
    base = parts[-1]
    return base == ".env" or (base.startswith(".env.") and base != ".env.example") or base in SECRET_BASENAMES


def check_read(tool, tool_input, project):
    root = os.path.realpath(project)
    for key in ("file_path", "path", "notebook_path"):
        v = tool_input.get(key)
        if v is None or v == "":
            continue  # no path: defaults inside the project, and ripgrep skips git-ignored files such as .env
        if not isinstance(v, str):
            return "unattended run: unreadable path"
        p = v if os.path.isabs(v) else os.path.join(project, v)
        real = os.path.realpath(p)
        if real != root and not real.startswith(root + os.sep):
            return "unattended run: reading outside the project is not allowed"
        if sensitive_name(p) or sensitive_name(real):
            return "unattended run: reading secret files is not allowed"
    for key in ("glob", "pattern"):
        v = tool_input.get(key)
        if isinstance(v, str) and (SENSITIVE_PATTERN.search(v) and not v.endswith(".env.example")):
            return "unattended run: file filter targets secret files"
    return None


def check_web(tool, tool_input):
    if tool != "WebFetch":
        return None
    url = tool_input.get("url")
    if not isinstance(url, str):
        return "unattended run: unreadable url"
    try:
        u = urllib.parse.urlsplit(url.strip())
    except ValueError:
        return "unattended run: unreadable url"
    if u.scheme != "https" or not u.hostname or u.username is not None or u.password is not None or "@" in u.netloc:
        return "unattended run: WebFetch needs a plain https URL"
    return None


def read_dotenv(path):
    out = {}
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.startswith("export "):
                    line = line[7:]
                k, _, v = line.partition("=")
                v = v.strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                    v = v[1:-1]
                out[k.strip()] = v
    except OSError:
        pass
    return out


def secret_values(project):
    pool = dict(read_dotenv(os.path.join(project, ".env")))
    pool.update(os.environ)
    return {v for k, v in pool.items() if re.search(r"KEY|TOKEN|SECRET|PASSWORD", k, re.I) and isinstance(v, str) and len(v) >= 8}


def forms(v):
    b = v.encode("utf-8")
    out = {v, urllib.parse.quote(v, safe=""), urllib.parse.quote_plus(v)}
    for enc in (base64.b64encode, base64.urlsafe_b64encode):
        e = enc(b).decode("ascii")
        out.update({e, e.rstrip("=")})
    return {x for x in out if len(x) >= 8}


def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield str(k)
            yield from strings(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from strings(v)


def contains_secret(tool_input, project):
    hay = json.dumps(tool_input, ensure_ascii=False) + "\n" + "\n".join(strings(tool_input))
    return any(f in hay for v in secret_values(project) for f in forms(v))


def check_write(path_value, project):
    if not isinstance(path_value, str) or not path_value:
        return "unattended run: write path missing"
    p = path_value if os.path.isabs(path_value) else os.path.join(project, path_value)
    real = os.path.realpath(p)  # resolves symlinks and ".."; works for a file that does not exist yet
    libdir = os.path.realpath(os.path.join(project, "outputs", "librarian"))
    if os.path.dirname(real) != libdir or not WRITE_NAMES.fullmatch(os.path.basename(real)):
        return "unattended run: write not allowed outside the librarian report and proposals files"
    return None


def decide():
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
    project = os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd")
    if not isinstance(project, str) or not project:
        deny("unattended run: project directory unknown")
    if contains_secret(tool_input, project):
        deny("unattended run: tool input contains a secret value")
    if tool == "Bash":
        cmd = tool_input.get("command")
        reason = check_bash(cmd if isinstance(cmd, str) else "\n", project)
    elif tool == "Write":
        reason = check_write(tool_input.get("file_path"), project)
    elif tool in ("Edit", "MultiEdit", "NotebookEdit"):
        reason = f"unattended run: {tool} is not allowed"
    elif tool in ("Read", "Grep", "Glob"):
        reason = check_read(tool, tool_input, project)
    elif tool in ("WebFetch", "WebSearch"):
        reason = check_web(tool, tool_input)
    elif tool.startswith("mcp__"):
        reason = None if tool in ALLOWED_MCP else "unattended run: tool not on the allowlist"
    else:
        reason = None  # tools this hook is not registered for are not its business
    if reason:
        deny(reason)


def main():
    if not is_active():
        return
    try:
        decide()
    except SystemExit:
        raise
    except BaseException:
        deny("unattended guard error")


if __name__ == "__main__":
    main()
