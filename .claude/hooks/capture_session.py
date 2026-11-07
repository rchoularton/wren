#!/usr/bin/env python3
"""
Opt-in session capture (dispatched detached by stop-session-capture.sh).

Extracts the last user/assistant exchange from a session transcript, summarizes
it into 2-5 third-person bullets via one headless `claude -p --model haiku`
call, and appends them to the dated log in the project's auto-memory dir:

    <memory>/context/sessions/YYYY-MM-DD.md

Only the local `claude` binary is called; nothing else is sent anywhere.
Idempotent: each exchange is hashed (session id + last assistant uuid) and
recorded in sessions/.captured, so repeated Stop events write nothing.
Errors never reach the session; they go to sessions/.capture_errors.log.

Paths derive at runtime: the memory dir from $CLAUDE_PROJECT_DIR, the binary
from $WREN_CLAUDE_BIN or PATH (no binary = give up silently).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

MODEL = "haiku"  # triage tier; canonical: .claude/lib/model-policy.mjs ALIASES.triage
CLAUDE_TIMEOUT_S = 120
MIN_EXCHANGE_CHARS = 300   # skip trivial exchanges ("next", "yes", etc.)
MAX_USER_CHARS = 1500
MAX_ASSISTANT_CHARS = 4500  # user + assistant excerpt stays at about 6,000 chars

SUMMARY_PROMPT = """You are a note-taker for a researcher's session log. Below is one \
exchange from a Claude Code session (user message, then assistant response).

Write 2-5 short third-person bullets of what was done and decided. Include \
decisions, instructions the user gave, results, and unresolved questions. Do not \
quote the user's text beyond a clause. Skip pleasantries and tool mechanics. \
NEVER include passwords, API keys, tokens, or other credentials; say \
"credentials configured" instead. If nothing durable happened (acknowledgement, \
navigation), reply with exactly: SKIP

Output ONLY lines starting with "- ", or SKIP. No heading, no preamble.

=== USER ===
{user}

=== ASSISTANT ===
{assistant}
"""


def memory_dir() -> Path:
    """~/.claude/projects/<slug>/memory; same logic as session-start-learnings.py."""
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    slug = re.sub(r"[/.]", "-", str(Path(root).resolve()))
    return Path.home() / ".claude" / "projects" / slug / "memory"


def sessions_dir() -> Path:
    return memory_dir() / "context" / "sessions"


def log_error(msg: str) -> None:
    try:
        d = sessions_dir()
        d.mkdir(parents=True, exist_ok=True)
        with open(d / ".capture_errors.log", "a") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} {' '.join(msg.split())}\n")
    except Exception:
        pass


def text_of(message: dict) -> str:
    """Concatenate text blocks of a transcript message; ignore tool blocks."""
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    return "\n".join(
        b.get("text", "") for b in content
        if isinstance(b, dict) and b.get("type") == "text"
    )


def last_exchange(transcript_path: Path):
    """Return (user_text, assistant_text, last_assistant_uuid) or None."""
    events = []
    with open(transcript_path) as f:
        for line in f:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    last_user_idx = None
    for i in range(len(events) - 1, -1, -1):
        e = events[i]
        if e.get("type") != "user" or e.get("isMeta"):
            continue
        txt = text_of(e.get("message", {}))
        # skip tool-result carriers and injected command output
        if not txt.strip() or txt.lstrip().startswith("<"):
            continue
        last_user_idx = i
        break
    if last_user_idx is None:
        return None

    user_text = text_of(events[last_user_idx].get("message", {}))
    parts, last_uuid = [], ""
    for e in events[last_user_idx + 1:]:
        if e.get("type") == "assistant":
            t = text_of(e.get("message", {}))
            if t.strip():
                parts.append(t)
                last_uuid = e.get("uuid", "") or last_uuid
    if not parts:
        return None
    return user_text, "\n".join(parts), last_uuid


def truncate(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    head, tail = int(cap * 0.6), int(cap * 0.35)
    return text[:head] + "\n[... truncated ...]\n" + text[-tail:]


def find_claude() -> str | None:
    override = os.environ.get("WREN_CLAUDE_BIN")
    if override:
        return override if os.path.exists(override) else None
    return shutil.which("claude")


# Sandbox flags for the headless call. The excerpt is untrusted text (it can
# contain pasted web content), so the summarizer gets no tools, no settings, no
# MCP servers and no session file. Verified present in `claude --help` of the
# installed CLI on 2026-11-07: --tools, --setting-sources, --strict-mcp-config,
# --no-session-persistence. NOT present: --max-turns (so it is not passed; with
# --tools "" the model cannot take extra turns anyway). Presence is re-checked at
# run time from `claude --help` (no session is started); a missing required flag
# means nothing is captured and the reason goes to .capture_errors.log.
REQUIRED_FLAGS = ("--tools", "--setting-sources", "--strict-mcp-config",
                  "--no-session-persistence")


def build_argv(claude: str) -> list[str]:
    return [claude, "-p", "--model", MODEL,
            "--tools", "", "--setting-sources", "", "--strict-mcp-config",
            "--no-session-persistence"]


def check_sandbox_flags(claude: str) -> None:
    out = subprocess.run([claude, "--help"], capture_output=True, text=True,
                         timeout=15, stdin=subprocess.DEVNULL)
    text = out.stdout + out.stderr
    missing = [f for f in REQUIRED_FLAGS if f not in text]
    if missing:
        raise RuntimeError(f"claude CLI lacks sandbox flags {missing}; not capturing")


def run_bounded(argv: list[str], prompt: str, env: dict) -> subprocess.CompletedProcess:
    """Run in its own process group; on timeout kill the whole group."""
    proc = subprocess.Popen(
        argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=str(Path.home()), env=env, start_new_session=True)
    try:
        out, err = proc.communicate(prompt, timeout=CLAUDE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            proc.kill()
        proc.communicate()
        raise
    return subprocess.CompletedProcess(argv, proc.returncode, out, err)


def summarize(user_text: str, assistant_text: str, claude: str) -> str | None:
    prompt = SUMMARY_PROMPT.format(
        user=truncate(user_text, MAX_USER_CHARS),
        assistant=truncate(assistant_text, MAX_ASSISTANT_CHARS),
    )
    check_sandbox_flags(claude)
    env = dict(os.environ, WREN_CAPTURE_HOOK="1")
    # Runs from $HOME so this project's CLAUDE.md and hooks never load.
    result = run_bounded(build_argv(claude), prompt, env)
    if result.returncode != 0:
        raise RuntimeError(f"claude -p failed rc={result.returncode}: {result.stderr[:300]}")
    out = result.stdout.strip()
    if not out or out.upper().startswith("SKIP"):
        return None
    bullets = [l.strip() for l in out.splitlines() if l.strip().startswith("- ")]
    return "\n".join(bullets[:5]) if bullets else None


def append_entry(bullets: str, session_id: str) -> Path:
    d = sessions_dir()
    d.mkdir(parents=True, exist_ok=True)
    day = datetime.now().strftime("%Y-%m-%d")
    log_file = d / f"{day}.md"
    if not log_file.exists():
        log_file.write_text(
            f"# Session log - {day}\n\n"
            "Auto-captured by the opt-in session-capture Stop hook "
            "(tiers.session_capture). One entry per exchange.\n"
        )
    stamp = datetime.now().strftime("%H:%M")
    short_id = (session_id or "unknown")[:8]
    with open(log_file, "a") as f:
        f.write(f"\n### {stamp} - session {short_id} (auto-captured)\n{bullets}\n")
    return log_file


def main() -> int:
    if len(sys.argv) < 2 or os.environ.get("WREN_CAPTURE_HOOK"):
        return 0
    transcript_path = Path(sys.argv[1])
    session_id = sys.argv[2] if len(sys.argv) > 2 else ""

    claude = find_claude()
    if not claude:
        return 0  # no claude binary: give up silently

    try:
        exchange = last_exchange(transcript_path)
        if exchange is None:
            return 0
        user_text, assistant_text, last_uuid = exchange
        if len(user_text) + len(assistant_text) < MIN_EXCHANGE_CHARS:
            return 0

        digest = hashlib.sha256(f"{session_id}:{last_uuid}".encode()).hexdigest()
        hashes = sessions_dir() / ".captured"
        seen = hashes.read_text().split() if hashes.exists() else []
        if digest in seen:
            return 0

        # Claim the exchange before summarising; a parallel helper exits quietly.
        sessions_dir().mkdir(parents=True, exist_ok=True)
        lock = sessions_dir() / f".lock-{digest}"
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        except FileExistsError:
            return 0
        try:
            bullets = summarize(user_text, assistant_text, claude)
            # Record the hash even on SKIP so the same exchange is never re-sent.
            with open(hashes, "a") as f:
                f.write(digest + "\n")
            if bullets:
                append_entry(bullets, session_id)
        finally:
            try:
                lock.unlink()
            except OSError:
                pass
        return 0
    except Exception as e:
        log_error(f"{type(e).__name__}: {e} (transcript={transcript_path})")
        return 0  # detached; never signal failure


if __name__ == "__main__":
    sys.exit(main())
