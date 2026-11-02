#!/usr/bin/env python3
"""
UserPromptSubmit hook: inject active-paper context.

Reads `.current_paper` and the paper's STATUS.md frontmatter (paper_id,
phase, tier, status, journal) and prepends a one-line context tag so
the model doesn't drift onto the wrong paper or phase.

Project root comes from $CLAUDE_PROJECT_DIR (portable). Silent if
.current_paper is missing or STATUS.md is unreadable.
"""
from __future__ import annotations

import json
import os
import select
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
CURRENT_FILE = PROJECT_ROOT / ".current_paper"


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    out = {}
    for line in text.split("\n")[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def read_stdin(first_wait: float = 1.0, idle_wait: float = 0.1) -> str:
    """Read stdin without ever blocking on an open pipe that never reaches EOF.

    Waits up to `first_wait` seconds for the first byte, then drains until EOF
    or `idle_wait` seconds of silence. Falls back to "" on any error.
    """
    buf = b""
    try:
        fd = sys.stdin.fileno()
        wait = first_wait
        while select.select([fd], [], [], wait)[0]:
            chunk = os.read(fd, 65536)
            if not chunk:
                break  # EOF
            buf += chunk
            wait = idle_wait
    except Exception:
        pass
    return buf.decode("utf-8", "replace")


def main() -> None:
    try:
        json.loads(read_stdin() or "{}")
    except Exception:
        pass

    if not CURRENT_FILE.exists():
        print(json.dumps({}))
        return

    paper_id = CURRENT_FILE.read_text().strip()
    if not paper_id:
        print(json.dumps({}))
        return

    status_path = PROJECT_ROOT / "papers" / paper_id / "STATUS.md"
    if not status_path.exists():
        block = f"## Active Paper\n`.current_paper` = **{paper_id}** (no STATUS.md found)"
        print(json.dumps({"additionalContext": block}))
        return

    try:
        fm = parse_frontmatter(status_path.read_text())
    except Exception:
        print(json.dumps({}))
        return

    fields = []
    for key in ("paper_id", "phase", "tier", "status", "journal"):
        if fm.get(key):
            fields.append(f"{key}={fm[key]}")

    title = fm.get("title", "")

    block = "## Active Paper\n"
    block += f"`.current_paper` = **{paper_id}**"
    if fields:
        block += " — " + ", ".join(fields)
    if title:
        block += f"\n_{title}_"
    block += "\n\nIf this work isn't about that paper, say so explicitly."

    print(json.dumps({"additionalContext": block}))


if __name__ == "__main__":
    main()
