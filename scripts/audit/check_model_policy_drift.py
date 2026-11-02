#!/usr/bin/env python3
"""
check_model_policy_drift.py — fail if model references drift from the policy file.

Reads MODEL_IDS and ALIASES from .claude/lib/model-policy.mjs, then checks:
  (a) every `model:` value in .claude/agents/*.md is one of the ALIASES values
  (b) any literal `claude-...` model id under .claude/, scripts/, docs/, README.md
      is one of the MODEL_IDS values
  (c) each MODEL_IDS entry looks current: no date suffix (-YYYYMMDD) and major
      version >= MIN_MAJOR

Exit 0 = clean. Exit 1 = findings (one line each).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
POLICY = Path(".claude/lib/model-policy.mjs")
SCAN = [".claude", "scripts", "docs", "README.md"]
MIN_MAJOR = 5
SKIP_SUFFIXES = {".png", ".pdf", ".jpg", ".jpeg", ".gif", ".docx", ".xlsx", ".ico", ".zip", ".pyc"}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv"}

MODEL_ID_RX = re.compile(r"\bclaude-(?:opus|sonnet|haiku)[-0-9a-z.]*", re.I)
# Trailing dashes/dots are prose punctuation, not part of an id.
TRAIL = "-."


def _object_pairs(text: str, name: str) -> dict[str, str]:
    m = re.search(rf"export const {name}\s*=\s*\{{(.*?)\}}", text, re.S)
    if not m:
        return {}
    return dict(re.findall(r"(\w+)\s*:\s*['\"]([^'\"]+)['\"]", m.group(1)))


def scan_files(root: Path):
    for entry in SCAN:
        base = root / entry
        if base.is_file():
            yield base
        elif base.is_dir():
            for p in sorted(base.rglob("*")):
                if p.is_file() and not (set(p.parts) & SKIP_DIRS) and p.suffix.lower() not in SKIP_SUFFIXES:
                    yield p


def check(root: Path) -> list[str]:
    findings: list[str] = []
    policy = root / POLICY
    if not policy.exists():
        return [f"{POLICY}: not found"]
    text = policy.read_text()
    ids = _object_pairs(text, "MODEL_IDS")
    aliases = _object_pairs(text, "ALIASES")
    if not ids or not aliases:
        return [f"{POLICY}: could not parse MODEL_IDS / ALIASES"]
    alias_set = set(aliases.values())
    id_set = set(ids.values())

    # (c) MODEL_IDS look current
    for alias, mid in ids.items():
        if re.search(r"-\d{8}$", mid):
            findings.append(f"{POLICY}: MODEL_IDS.{alias} '{mid}' has a date suffix")
        m = re.match(r"claude-[a-z]+-(\d+)", mid)
        if not m or int(m.group(1)) < MIN_MAJOR:
            findings.append(f"{POLICY}: MODEL_IDS.{alias} '{mid}' is below major version {MIN_MAJOR}")

    # (a) agent frontmatter aliases
    for f in sorted((root / ".claude" / "agents").glob("*.md")):
        fm = re.match(r"---\n(.*?)\n---", f.read_text(), re.S)
        if not fm:
            continue
        m = re.search(r"^model:\s*(\S+)", fm.group(1), re.M)
        if m and m.group(1).strip("'\"") not in alias_set:
            findings.append(
                f"{f.relative_to(root)}: model '{m.group(1)}' is not a policy alias {sorted(alias_set)}"
            )

    # (b) literal ids anywhere
    for p in scan_files(root):
        rel = p.relative_to(root)
        try:
            lines = p.read_text(errors="ignore").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines, 1):
            for hit in MODEL_ID_RX.findall(line):
                hit = hit.rstrip(TRAIL)
                if hit not in id_set:
                    findings.append(f"{rel}:{i}: model id '{hit}' not in MODEL_IDS")
    return findings


def main() -> None:
    findings = check(PROJECT_ROOT)
    if findings:
        print("✗ model-policy drift:\n")
        print("\n".join(f"  {f}" for f in findings))
        print(f"\n{len(findings)} finding(s).")
        sys.exit(1)
    print("✓ model-policy drift check clean.")


if __name__ == "__main__":
    main()
