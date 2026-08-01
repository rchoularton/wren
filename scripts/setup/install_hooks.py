#!/usr/bin/env python3
"""
install_hooks.py — make the Claude Code hooks executable and sanity-check deps.

Hooks are wired declaratively in .claude/settings.json via $CLAUDE_PROJECT_DIR,
so there is nothing to copy. This script just:
  - chmod +x the hook scripts
  - confirm python3 is available (the .py hooks need it)
  - warn (do not fail) if terminal-notifier is missing on macOS
"""
from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = PROJECT_ROOT / ".claude" / "hooks"
MEMORY_SEED = PROJECT_ROOT / ".claude" / "memory-seed" / "MEMORY.md"


def seed_memory_dir() -> None:
    """Create the Claude Code per-project memory dir and seed MEMORY.md if absent."""
    # Single source of truth for the slug (same script dir on sys.path).
    from render_templates import derive_memory_slug
    slug = derive_memory_slug(str(PROJECT_ROOT))
    mem = Path.home() / ".claude" / "projects" / slug / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    target = mem / "MEMORY.md"
    if not target.exists() and MEMORY_SEED.exists():
        target.write_text(MEMORY_SEED.read_text())
        print(f"  ✓ seeded {target}")
    else:
        print(f"  · memory dir ready: {mem}")


def make_executable(path: Path) -> None:
    st = path.stat()
    path.chmod(st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> None:
    if not HOOKS_DIR.exists():
        print("No .claude/hooks directory — skipping hook install.")
        return

    made = []
    for hook in sorted(HOOKS_DIR.iterdir()):
        if hook.suffix in (".py", ".sh"):
            make_executable(hook)
            made.append(hook.name)

    print("Made hooks executable:")
    for m in made:
        print(f"  ✓ {m}")

    print("Cross-session memory:")
    seed_memory_dir()

    if not shutil.which("python3"):
        sys.exit("python3 not found on PATH — the Python hooks will not run.")

    if sys.platform == "darwin" and not shutil.which("terminal-notifier"):
        print(
            "\nNote: terminal-notifier not found. macOS notifications will be "
            "silent (RUNNING.md logging still works). Install with:\n"
            "  brew install terminal-notifier"
        )


if __name__ == "__main__":
    main()
