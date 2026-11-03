#!/usr/bin/env python3
"""Regenerate the papers table in papers/README.md from STATUS.md frontmatter.

Rewrites only the text between `<!-- papers:begin -->` and `<!-- papers:end -->`.
Idempotent: a second run changes nothing.

Usage:
    python3 scripts/utils/papers_table.py [--repo DIR]
Entry point for: npm run papers:table
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wren_status import build, papers_table  # noqa: E402

BEGIN, END = "<!-- papers:begin -->", "<!-- papers:end -->"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, default=None, help="project root (default: cwd)")
    args = ap.parse_args(argv)
    repo = (args.repo or Path.cwd()).resolve()
    readme = repo / "papers" / "README.md"
    if not (repo / "papers").is_dir():
        print(f"papers_table: no papers/ directory in {repo}", file=sys.stderr)
        return 2
    if not readme.is_file():
        print(f"papers_table: {readme} not found", file=sys.stderr)
        return 1
    text = readme.read_text(encoding="utf-8")
    head, sep1, rest = text.partition(BEGIN)
    _, sep2, tail = rest.partition(END)
    if not (sep1 and sep2):
        print(f"papers_table: {readme} needs {BEGIN} and {END} markers", file=sys.stderr)
        return 1
    table = papers_table(build(repo)["papers"])
    new = f"{head}{BEGIN}\n{table}\n{END}{tail}"
    if new != text:
        readme.write_text(new, encoding="utf-8")
        print(f"updated {readme}")
    else:
        print("papers table already up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
