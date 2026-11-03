#!/usr/bin/env python3
"""Standing-context size report: what Wren loads into every session.

Prints bytes and an ESTIMATED token count (bytes / 4; a rough proxy, not a
tokenizer) for each standing-context source, then a total:

  - CLAUDE.template.md (rendered to CLAUDE.md in a user's project)
  - each file in .claude/rules/
  - .claude/memory-seed/MEMORY.md
  - each agent's `description:` field in .claude/agents/*.md
  - the maximum injection of the two SessionStart hooks, measured by running
    each hook against a scaffold fixture filled to its caps

Usage:
  python3 scripts/utils/context_size.py
  python3 scripts/utils/context_size.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BYTES_PER_TOKEN = 4  # estimate only


def _size(text: str) -> int:
    return len(text.encode("utf-8"))


def _agent_description(path: Path) -> str:
    """The frontmatter `description:` value (quoted or bare, single line)."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    if not m:
        return ""
    for line in m.group(1).splitlines():
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return ""


def _load_hook_caps() -> tuple[int, int]:
    src = (REPO_ROOT / ".claude" / "hooks" / "session-start-learnings.py").read_text()
    learnings = int(re.search(r"^MAX_LEARNINGS\s*=\s*(\d+)", src, re.M).group(1))
    decisions = int(re.search(r"^MAX_AUTHOR_DECISIONS\s*=\s*(\d+)", src, re.M).group(1))
    return learnings, decisions


def _run_hook(hook: Path, event: dict, env: dict) -> str:
    base = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    proc = subprocess.run(
        [sys.executable, str(hook)], input=json.dumps(event),
        capture_output=True, text=True, env={**base, **env}, timeout=30,
    )
    try:
        return json.loads(proc.stdout).get("additionalContext", "")
    except Exception:
        return ""


def hook_injections() -> dict[str, int]:
    """Bytes injected by each SessionStart hook with every cap filled."""
    max_learnings, max_decisions = _load_hook_caps()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        root = tmp_path / "project"
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "settings.local.json")
        shutil.copytree(REPO_ROOT / ".claude", root / ".claude", ignore=ignore)
        shutil.copytree(REPO_ROOT / "papers" / "example-paper",
                        root / "papers" / "example-paper", ignore=ignore)
        shutil.copy(REPO_ROOT / "research-config.example.yml", root / "research-config.yml")
        (root / ".current_paper").write_text("example-paper\n")
        # Over-cap, over-length AUTHOR DECISION lines so the cap and snippet limit bind.
        extra = root / "papers" / "example-paper" / "decisions.md"
        extra.write_text("".join(
            f"AUTHOR DECISION: {'x' * 200} {i}\n" for i in range(max_decisions + 2)))
        # Fake learnings, dated today so they fall inside the lookback window.
        home = tmp_path / "home"
        slug = re.sub(r"[/.]", "-", str(root.resolve()))
        mem = home / ".claude" / "projects" / slug / "memory"
        mem.mkdir(parents=True)
        today = datetime.now().strftime("%Y-%m-%d")
        for i in range(max_learnings + 2):
            (mem / f"learning_{today}_{i:02d}.md").write_text(
                f"---\nname: fake learning number {i} with a typical-length title\n"
                f"type: learning\n---\nbody\n")
        env = {"CLAUDE_PROJECT_DIR": str(root), "HOME": str(home)}
        hooks = REPO_ROOT / ".claude" / "hooks"
        learnings = _run_hook(hooks / "session-start-learnings.py", {"source": "compact"}, env)
        welcome = _run_hook(hooks / "session-start-welcome.py", {}, env)
    return {
        "session-start-learnings (max, compact)": _size(learnings),
        "session-start-welcome (max)": _size(welcome),
    }


def measure() -> list[tuple[str, str, int]]:
    """Rows of (group, name, bytes)."""
    rows: list[tuple[str, str, int]] = []
    tpl = REPO_ROOT / "CLAUDE.template.md"
    rows.append(("template", "CLAUDE.template.md", _size(tpl.read_text(encoding="utf-8"))))
    for f in sorted((REPO_ROOT / ".claude" / "rules").glob("*.md")):
        rows.append(("rules", f".claude/rules/{f.name}", _size(f.read_text(encoding="utf-8"))))
    mem = REPO_ROOT / ".claude" / "memory-seed" / "MEMORY.md"
    rows.append(("memory", ".claude/memory-seed/MEMORY.md", _size(mem.read_text(encoding="utf-8"))))
    for f in sorted((REPO_ROOT / ".claude" / "agents").glob("*.md")):
        desc = _agent_description(f)
        if desc:  # skips README.md and other non-agent files
            rows.append(("agents", f"agent description: {f.stem}", _size(desc)))
    for name, n in hook_injections().items():
        rows.append(("hooks", name, n))
    return rows


def total(rows: list[tuple[str, str, int]]) -> int:
    return sum(n for _, _, n in rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()
    rows = measure()
    if args.json:
        print(json.dumps({"rows": rows, "total_bytes": total(rows)}))
        return
    width = max(len(name) for _, name, _ in rows)
    print(f"{'source':<{width}}  {'bytes':>7}  {'~tokens (est.)':>14}")
    print("-" * (width + 25))
    for _, name, n in rows:
        print(f"{name:<{width}}  {n:>7}  {n // BYTES_PER_TOKEN:>14}")
    print("-" * (width + 25))
    t = total(rows)
    print(f"{'TOTAL':<{width}}  {t:>7}  {t // BYTES_PER_TOKEN:>14}")
    print(f"\nTokens are an estimate: bytes / {BYTES_PER_TOKEN}.")


if __name__ == "__main__":
    main()
