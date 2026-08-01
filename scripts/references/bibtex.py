#!/usr/bin/env python3
"""
Minimal BibTeX reader — the universal reference adapter.

Reads the .bib file named in research-config.yml (references.bibtex_path) and
provides list/lookup/search over entries, with no external dependencies. Any
reference manager (Zotero, Mendeley, EndNote, Paperpile) can export to this
format, so this adapter works for everyone.

CLI:
    python3 scripts/references/bibtex.py list
    python3 scripts/references/bibtex.py get <citekey>
    python3 scripts/references/bibtex.py search <term>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,]+),(.*?)\n\}", re.DOTALL)
FIELD_RE = re.compile(r"(\w+)\s*=\s*[{\"](.+?)[}\"]\s*,?\s*(?=\n\s*\w+\s*=|\n?$)", re.DOTALL)


def bibtex_path() -> Path:
    """Read references.bibtex_path from research-config.yml (fallback default)."""
    default = PROJECT_ROOT / "references" / "library.bib"
    cfg = PROJECT_ROOT / "research-config.yml"
    if cfg.exists():
        try:
            import yaml  # type: ignore
            data = yaml.safe_load(cfg.read_text()) or {}
            rel = (data.get("references") or {}).get("bibtex_path")
            if rel:
                return PROJECT_ROOT / rel
        except Exception:
            pass
    return default


def parse(text: str) -> list[dict]:
    entries = []
    for etype, key, body in ENTRY_RE.findall(text):
        fields = {}
        for fname, fval in FIELD_RE.findall(body):
            fields[fname.lower().strip()] = re.sub(r"\s+", " ", fval).strip()
        fields["_type"] = etype.lower()
        fields["_key"] = key.strip()
        entries.append(fields)
    return entries


def load() -> list[dict]:
    p = bibtex_path()
    if not p.exists():
        # Fall back to the shipped example if the user hasn't added a library yet
        example = PROJECT_ROOT / "references" / "library.bib.example"
        if example.exists():
            print(f"(no {p.name} yet — reading {example.name}; export your library to {p})",
                  file=sys.stderr)
            return parse(example.read_text())
        return []
    return parse(p.read_text())


def _fmt(e: dict) -> str:
    who = e.get("author", "?").split(" and ")[0]
    return f"{e['_key']}: {who} ({e.get('year','?')}) — {e.get('title','')[:70]}"


def main() -> None:
    args = sys.argv[1:]
    cmd = args[0] if args else "list"
    entries = load()

    if cmd == "list":
        for e in entries:
            print(_fmt(e))
        print(f"\n{len(entries)} entries in {bibtex_path()}")
    elif cmd == "get" and len(args) > 1:
        hits = [e for e in entries if e["_key"].lower() == args[1].lower()]
        if not hits:
            print(f"No entry with citekey '{args[1]}'.")
            sys.exit(1)
        for k, v in hits[0].items():
            print(f"{k}: {v}")
    elif cmd == "search" and len(args) > 1:
        term = args[1].lower()
        hits = [e for e in entries if term in " ".join(e.values()).lower()]
        for e in hits:
            print(_fmt(e))
        print(f"\n{len(hits)} match(es) for '{args[1]}'")
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
