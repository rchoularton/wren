#!/usr/bin/env python3
"""
SessionStart hook: nudge a fresh Wren project toward guided onboarding.

On a project that looks like Wren (research-config.yml present) but has not yet
completed onboarding (no .wren/onboarded marker), inject a one-line pointer to
`/setup wren`. Once `/setup wren` writes the marker in its final phase, this hook
goes silent — so the nudge shows once, not every session.

Paths are derived from $CLAUDE_PROJECT_DIR (falling back to cwd), so this works in
any clone with no hardcoded paths. Mirrors session-start-learnings.py.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def project_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def main() -> None:
    # Drain stdin (hook receives a JSON event); ignore its contents.
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    root = project_root()

    # Only speak up inside a Wren project.
    if not (root / "research-config.yml").exists():
        print(json.dumps({}))
        return

    # Silent once onboarding is done.
    if (root / ".wren" / "onboarded").exists():
        print(json.dumps({}))
        return

    block = (
        "🐦 New Wren project — run `/setup wren` for a guided tour and to set up your "
        "first paper. (Or `/paper` to jump straight in.)"
    )
    print(json.dumps({"additionalContext": block}))


if __name__ == "__main__":
    main()
