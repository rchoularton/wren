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
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

LOOKBACK_DAYS = 7
MAX_LEARNINGS = 10
MAX_AUTHOR_DECISIONS = 8
AUTHOR_DECISION_SNIPPET = 160


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


def project_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def latest_freeze_tag(root: Path, paper_id: str) -> str:
    """Highest-numbered `{paper_id}-gold-v{n}` git tag, or "" if none/no git."""
    try:
        out = subprocess.run(
            ["git", "tag", "--list", f"{paper_id}-gold-v*"],
            cwd=str(root), capture_output=True, text=True, timeout=5,
        ).stdout
    except Exception:
        return ""
    pat = re.compile(rf"^{re.escape(paper_id)}-gold-v(\d+)$")
    best = (-1, "")
    for tag in out.split():
        m = pat.match(tag)
        if m and int(m.group(1)) > best[0]:
            best = (int(m.group(1)), tag)
    return best[1]


def author_decisions(root: Path, paper_dir: Path) -> List[str]:
    """`path:line — snippet` for AUTHOR DECISION lines in the paper's .md files."""
    hits: List[str] = []
    for f in sorted(paper_dir.rglob("*.md")):
        rel = f.relative_to(root)
        if any(part.startswith("_archived") for part in f.relative_to(paper_dir).parts):
            continue
        try:
            text = f.read_text(errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if "AUTHOR DECISION" in line:
                snip = line.strip()
                if len(snip) > AUTHOR_DECISION_SNIPPET:
                    snip = snip[:AUTHOR_DECISION_SNIPPET].rstrip() + "…"
                hits.append(f"- `{rel}:{i}` — {snip}")
                if len(hits) >= MAX_AUTHOR_DECISIONS:
                    return hits
    return hits


def get_pinned_anchors() -> str:
    """Live paper state re-injected after compaction; "" on any problem."""
    try:
        root = project_root()
        cp = root / ".current_paper"
        if not cp.exists():
            return ""
        paper_id = cp.read_text().strip()
        if not paper_id:
            return ""
        paper_dir = root / "papers" / paper_id
        lines = [f"**Current paper:** `{paper_id}`"]
        try:
            fm = parse_frontmatter((paper_dir / "STATUS.md").read_text())
        except Exception:
            fm = {}
        for key in ("title", "phase", "tier", "status", "journal"):
            if fm.get(key):
                lines.append(f"**{key.capitalize()}:** {fm[key]}")
        tag = latest_freeze_tag(root, paper_id)
        if tag:
            lines.append(f"**Latest freeze:** `{tag}`")
        decisions = author_decisions(root, paper_dir)
        if decisions:
            lines.append("**Recorded author decisions:**")
            lines.extend(decisions)
        return (
            "## Pinned Anchors (re-pinned across compaction)\n"
            "Live project state that a compaction summary tends to blur; "
            "treat it as current.\n\n" + "\n".join(lines)
        )
    except Exception:
        return ""


def main() -> None:
    source = None
    try:
        data = json.load(sys.stdin)
        if isinstance(data, dict):
            source = data.get("source")
    except Exception:
        pass

    anchors = get_pinned_anchors() if source == "compact" else ""

    learnings = get_recent_learnings(memory_dir())
    if not learnings:
        print(json.dumps({"additionalContext": anchors} if anchors else {}))
        return

    block = "## Recent Session Learnings (last 7 days)\n"
    block += "Captured via /retro from previous sessions:\n"
    block += "\n".join(learnings)
    block += "\n\nReview relevant learning_*.md files in memory/ if pertinent to today's work."
    if anchors:
        block = anchors + "\n\n" + block

    print(json.dumps({"additionalContext": block}))


if __name__ == "__main__":
    main()
