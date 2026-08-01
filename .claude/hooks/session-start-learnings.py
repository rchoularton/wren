#!/usr/bin/env python3
"""
SessionStart hook: surface recent learnings.

Injects a block of recent /retro learnings (learning_*.md from the last 7 days)
into session-start context so hard-won insights stay visible.

The Claude Code per-project memory directory is derived at runtime from
$CLAUDE_PROJECT_DIR (no hardcoded path), so this works in any clone.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

LOOKBACK_DAYS = 7
MAX_LEARNINGS = 10


def memory_dir() -> Path:
    """Locate ~/.claude/projects/<slug>/memory for the current project.

    Claude Code slugifies the absolute project path by replacing '/' and '.'
    with '-'. We reproduce that from $CLAUDE_PROJECT_DIR (or cwd as fallback).
    """
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    slug = re.sub(r"[/.]", "-", str(Path(root).resolve()))
    return Path.home() / ".claude" / "projects" / slug / "memory"


def parse_frontmatter(content: str) -> dict:
    if not content.startswith("---"):
        return {}
    out = {}
    for line in content.split("\n")[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def get_recent_learnings(mem: Path) -> List[str]:
    if not mem.exists():
        return []
    cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
    learnings = []
    for f in sorted(mem.glob("learning_*.md"), reverse=True):
        parts = f.stem.split("_", 2)
        if len(parts) < 3:
            continue
        try:
            file_date = datetime.strptime(parts[1], "%Y-%m-%d")
        except ValueError:
            continue
        if file_date < cutoff:
            break
        fm = parse_frontmatter(f.read_text())
        name = fm.get("name", "")
        label = fm.get("domain") or fm.get("type") or "learning"
        if name:
            learnings.append(f"- [{label}] {name} ({parts[1]})")
    return learnings[:MAX_LEARNINGS]


def main() -> None:
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    learnings = get_recent_learnings(memory_dir())
    if not learnings:
        print(json.dumps({}))
        return

    block = "## Recent Session Learnings (last 7 days)\n"
    block += "Captured via /retro from previous sessions:\n"
    block += "\n".join(learnings)
    block += "\n\nReview relevant learning_*.md files in memory/ if pertinent to today's work."

    print(json.dumps({"additionalContext": block}))


if __name__ == "__main__":
    main()
