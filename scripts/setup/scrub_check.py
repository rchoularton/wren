#!/usr/bin/env python3
"""
scrub_check.py — fail if secrets or machine-specific paths leak into the
publishable (non-gitignored) file set.

Scans the files git would publish (tracked + untracked-not-ignored) for:
  - literal secret assignments (API_KEY / TOKEN / SECRET / PASSWORD = <value>)
  - absolute user home paths (/Users/<name>/ or /home/<name>/)
  - institution OneDrive paths ("OneDrive - <org>")

Rendered, user-specific files (CLAUDE.md, .mcp.json, .env, research-config.yml,
.claude/settings.local.json) are git-ignored, so a user's own paths/keys are
never scanned — this gate protects the shared template payload only.

Exit 0 = clean. Exit 1 = findings (printed). Run before publishing.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# (label, compiled regex). Designed to avoid flagging commented/placeholder examples.
PATTERNS = [
    (
        "literal secret assignment",
        # keyword = value, where value is a 16+ char literal that does NOT start
        # with '$' (env ref) or '-' (a ${VAR:-default} operator). This catches
        # `ZOTERO_API_KEY=cJtZ...` but not `SECRET: "${DIRECTUS_SECRET:-x}"`.
        re.compile(
            r'(?i)(api[_-]?key|token|secret|password|client[_-]?secret)'
            r'\s*[=:]\s*["\']?(?!\$)[A-Za-z0-9_][A-Za-z0-9_\-]{15,}'
        ),
    ),
    ("absolute user home path", re.compile(r"/(Users|home)/[A-Za-z0-9._-]+/")),
    # Real business OneDrive folders are "OneDrive - <Org>" (spaces around the
    # hyphen). Require the spaces so prose like "OneDrive-specific" isn't flagged.
    ("institution OneDrive path", re.compile(r"OneDrive\s+-\s+[A-Za-z]")),
]

# Lines matching these are ignored (commented-out env examples, doc placeholders).
SAFE_LINE = re.compile(r'^\s*#')
# Skip binary-ish / irrelevant extensions.
SKIP_SUFFIXES = {".png", ".pdf", ".jpg", ".jpeg", ".gif", ".docx", ".xlsx", ".ico", ".zip"}

# Rendered / user-specific files that are gitignored and legitimately contain the
# user's own home path, email, or keys. They are never part of the publishable
# payload, so the fallback walk (used when there's no git repo) must exclude them
# too — otherwise a scaffolded project's own research-config.yml trips the gate.
RENDERED = {
    "research-config.yml",
    ".env",
    "CLAUDE.md",
    "CLAUDE_REFERENCE.md",
    ".mcp.json",
    "data/docker-compose.directus.yml",
    ".claude/settings.local.json",
    ".claude/hooks/protected_paths.txt",
}


def publishable_files() -> list[Path]:
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        files = [PROJECT_ROOT / line for line in out.splitlines() if line]
        if files:
            return files
    except Exception:
        pass
    # Fallback (no git repo): walk, skipping obvious ignores AND the rendered set.
    skip_dirs = {"node_modules", ".git", "__pycache__", ".venv", "venv"}
    files = []
    for p in PROJECT_ROOT.rglob("*"):
        if not p.is_file() or (set(p.parts) & skip_dirs):
            continue
        rel = p.relative_to(PROJECT_ROOT).as_posix()
        if rel in RENDERED:
            continue
        files.append(p)
    return files


def main() -> None:
    findings = []
    for path in publishable_files():
        if path.suffix.lower() in SKIP_SUFFIXES or not path.exists():
            continue
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if SAFE_LINE.match(line):
                continue
            for label, rx in PATTERNS:
                if rx.search(line):
                    rel = path.relative_to(PROJECT_ROOT)
                    findings.append(f"  {rel}:{i}  [{label}]  {line.strip()[:100]}")

    if findings:
        print("✗ scrub_check found potential leaks:\n")
        print("\n".join(findings))
        print(f"\n{len(findings)} finding(s). Fix before publishing.")
        sys.exit(1)

    print("✓ scrub_check clean — no secrets or machine-specific paths in the publishable tree.")


if __name__ == "__main__":
    main()
