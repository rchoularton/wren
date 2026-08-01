"""
Ambient notifications for long-running scripts.

Posts desktop notifications (macOS terminal-notifier) and appends status
events to RUNNING.md in the project root. Use for any script that typically
runs more than ~2 minutes. Degrades gracefully: if terminal-notifier is not
installed (e.g. on Linux), notifications are skipped and RUNNING.md logging
still works.

Usage (context manager, preferred):
    from scripts.utils.notify import notify_run

    with notify_run("data extraction", "papers/example-paper"):
        # long-running work here
        ...
    # START logged on enter, DONE (with duration) on success, ERROR on exception.

Usage (manual events):
    from scripts.utils.notify import notify
    notify("START", "My Script")
    ...
    notify("DONE", "My Script", duration_s=123.4)

Notification grouping uses the NOTIFY_GROUP env var (default "research-assistant").
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from scripts.utils.paths import PROJECT_ROOT

RUNNING_MD = PROJECT_ROOT / "RUNNING.md"

# Locate terminal-notifier portably; fall back to the common Homebrew path.
_TERMINAL_NOTIFIER = shutil.which("terminal-notifier") or "/opt/homebrew/bin/terminal-notifier"
_NOTIFY_GROUP = os.environ.get("NOTIFY_GROUP", "research-assistant")

# Sound names per event type (macOS built-in sounds)
_SOUNDS = {
    "START": None,       # silent on start
    "DONE": "Glass",
    "ERROR": "Basso",
}

# Prefix for RUNNING.md legibility
_PREFIX = {
    "START": "▶",
    "DONE": "✓",
    "ERROR": "✗",
}


def _post_notification(event: str, script: str, detail: str = "") -> None:
    """Fire a desktop notification via terminal-notifier. Silent on failure."""
    if not Path(_TERMINAL_NOTIFIER).exists():
        return
    title = f"{event}: {script}"
    message = detail or script
    cmd = [_TERMINAL_NOTIFIER, "-title", title, "-message", message, "-group", _NOTIFY_GROUP]
    sound = _SOUNDS.get(event)
    if sound:
        cmd.extend(["-sound", sound])
    try:
        subprocess.run(cmd, check=False, capture_output=True, timeout=5)
    except Exception:
        pass  # notifications are best-effort


def _append_running_md(event: str, script: str, detail: str = "", duration_s: float | None = None) -> None:
    """Append an event line to RUNNING.md."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = [f"- {_PREFIX.get(event, '·')} `{ts}` **{event}** {script}"]
    if duration_s is not None:
        parts.append(f"({_fmt_duration(duration_s)})")
    if detail:
        parts.append(f"— {detail}")
    line = " ".join(parts) + "\n"
    try:
        if not RUNNING_MD.exists():
            RUNNING_MD.write_text("# Running Scripts\n\nLive log of notification events. Git-ignored.\n\n")
        with RUNNING_MD.open("a") as f:
            f.write(line)
    except Exception:
        pass  # logging is best-effort


def _fmt_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m"


def notify(event: str, script: str, detail: str = "", duration_s: float | None = None) -> None:
    """Emit a notification event.

    Args:
        event: One of "START", "DONE", "ERROR"
        script: Short name of the script/task
        detail: Optional extra context
        duration_s: Elapsed seconds (for DONE events)
    """
    _append_running_md(event, script, detail, duration_s)
    _post_notification(event, script, detail)


@contextmanager
def notify_run(script: str, detail: str = ""):
    """Context manager wrapping a long-running task with START/DONE/ERROR events."""
    notify("START", script, detail)
    t0 = time.monotonic()
    try:
        yield
    except Exception as e:
        notify("ERROR", script, detail=f"{type(e).__name__}: {e}")
        raise
    else:
        notify("DONE", script, detail=detail, duration_s=time.monotonic() - t0)


if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "notify-smoke-test"
    with notify_run(name, "manual smoke test"):
        time.sleep(1.2)
    print(f"Notification smoke test complete for '{name}'. See {RUNNING_MD}")
