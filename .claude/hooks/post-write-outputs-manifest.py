#!/usr/bin/env python3
"""
PostToolUse hook for Write/Edit/MultiEdit.

Per .claude/rules/outputs.md: new outputs/ subdirectories should be registered
in outputs/MANIFEST.md. This hook detects writes that create a new top-level
outputs/<dir>/ and surfaces a one-line reminder.

Project root comes from $CLAUDE_PROJECT_DIR (portable). Silent for writes to
existing outputs/ subdirs, writes outside outputs/, and MANIFEST.md itself.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
MANIFEST = OUTPUTS_DIR / "MANIFEST.md"


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        return

    ti = payload.get("tool_input", {}) or {}
    target = ti.get("file_path") or ti.get("path") or ""
    if not target:
        print(json.dumps({}))
        return

    try:
        target_path = Path(target).resolve()
        rel = target_path.relative_to(OUTPUTS_DIR.resolve())
    except (ValueError, Exception):
        print(json.dumps({}))
        return

    if target_path == MANIFEST.resolve():
        print(json.dumps({}))
        return

    parts = rel.parts
    if len(parts) < 2:
        print(json.dumps({}))
        return

    top = parts[0]
    if top.startswith("_") or top.startswith("ARCHIVED"):
        print(json.dumps({}))
        return

    if not MANIFEST.exists():
        print(json.dumps({}))
        return

    try:
        manifest_text = MANIFEST.read_text()
    except Exception:
        print(json.dumps({}))
        return

    if f"outputs/{top}/" in manifest_text or f"`{top}/`" in manifest_text or f"`{top}`" in manifest_text:
        print(json.dumps({}))
        return

    msg = (
        f"New outputs/ subdirectory `{top}/` is not in MANIFEST.md. "
        "Per .claude/rules/outputs.md, add a one-line entry describing what it holds "
        "and which paper/script produced it."
    )
    print(json.dumps({"systemMessage": msg}))


if __name__ == "__main__":
    main()
