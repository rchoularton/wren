#!/usr/bin/env python3
"""
render_templates.py — turn *.template.* files into concrete, user-specific files.

Reads research-config.yml, derives tokens (including the Claude Code per-project
memory slug), walks the tree for `*.template.*` files, substitutes {{TOKENS}},
and writes the rendered file with the `.template` segment removed. Also renders
.mcp.json from .mcp.json.template with conditional connector blocks.

Idempotent — safe to re-run after editing research-config.yml.

Requires PyYAML (see requirements.txt). Falls back to a clear message if absent.
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "research-config.yml"


def load_config() -> dict:
    try:
        import yaml  # type: ignore
    except ImportError:
        sys.exit(
            "PyYAML is required. Install it with:\n"
            "  python3 -m pip install pyyaml\n"
            "then re-run ./setup.sh"
        )
    if not CONFIG_PATH.exists():
        sys.exit(
            f"No {CONFIG_PATH.name} found. Copy research-config.example.yml to "
            "research-config.yml (or run the scaffolder) first."
        )
    with CONFIG_PATH.open() as f:
        return yaml.safe_load(f) or {}


def derive_memory_slug(root: str) -> str:
    """Claude Code stores per-project memory under ~/.claude/projects/<slug>/.

    The slug is the absolute project path with every non-alphanumeric character
    (path separators, dots, spaces, underscores, …) replaced by a hyphen, so a
    leading separator becomes a leading hyphen. This mirrors Claude Code's own
    cwd→slug encoding: anything short of it (e.g. leaving spaces intact) yields a
    slug Claude Code never looks under, so cross-session memory silently fails.
    """
    p = str(Path(root).resolve())
    return re.sub(r"[^A-Za-z0-9]", "-", p)


def dig(cfg: dict, *keys, default=""):
    cur = cfg
    for k in keys:
        if not isinstance(cur, dict) or k not in cur or cur[k] is None:
            return default
        cur = cur[k]
    return cur


def homebrew_node_path() -> str:
    """Return the keg-only node bin dir if present (macOS), else empty."""
    import glob
    for pattern in ("/opt/homebrew/opt/node@*/bin", "/usr/local/opt/node@*/bin"):
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[-1]
    return ""


def build_tokens(cfg: dict) -> dict:
    root = dig(cfg, "project", "root") or str(PROJECT_ROOT)
    protected = dig(cfg, "paths", "protected_write_paths", default=[]) or []
    tokens = {
        "PROJECT_NAME": dig(cfg, "project", "name", default="My Research Assistant"),
        "PROJECT_NAMESPACE": dig(cfg, "project", "namespace", default="myresearch"),
        "PROJECT_DISCIPLINE": dig(cfg, "project", "discipline", default="my research field"),
        "PROJECT_ROOT": str(Path(root).resolve()),
        "AUTHOR_NAME": dig(cfg, "identity", "author_name", default="Researcher"),
        "AUTHOR_ORCID": dig(cfg, "identity", "orcid", default=""),
        "AUTHOR_EMAIL": dig(cfg, "identity", "email", default=""),
        "MEMORY_SLUG": derive_memory_slug(root),
        "JOURNAL_DEFAULT": dig(cfg, "journals", "default", default="Target Journal"),
        "DATABASE_BACKEND": dig(cfg, "database", "backend", default="files"),
        "REFERENCE_PROVIDER": dig(cfg, "references", "provider", default="bibtex"),
        "BIBTEX_PATH": dig(cfg, "references", "bibtex_path", default="references/library.bib"),
        "HOMEBREW_NODE_PATH": homebrew_node_path(),
        "TODAY": date.today().isoformat(),
        # A newline-joined bash array literal for the safety guard
        "PROTECTED_PATHS": " ".join(f'"{p}"' for p in protected),
    }
    return tokens


def substitute(text: str, tokens: dict) -> str:
    def repl(m):
        key = m.group(1)
        return str(tokens.get(key, m.group(0)))
    return re.sub(r"\{\{([A-Z_]+)\}\}", repl, text)


def render_template_files(tokens: dict) -> list[str]:
    """Render every *.template.* file to its concrete name."""
    rendered = []
    for tmpl in PROJECT_ROOT.rglob("*.template.*"):
        if "node_modules" in tmpl.parts or ".git" in tmpl.parts:
            continue
        # foo.template.md -> foo.md ; .mcp.json.template handled separately below
        target = tmpl.with_name(tmpl.name.replace(".template", ""))
        text = substitute(tmpl.read_text(), tokens)
        target.write_text(text)
        rendered.append(str(target.relative_to(PROJECT_ROOT)))
    return rendered


def render_mcp(cfg: dict, tokens: dict) -> str | None:
    """Assemble .mcp.json enabling only the connectors the config turns on."""
    tmpl = PROJECT_ROOT / ".mcp.json.template"
    if not tmpl.exists():
        return None
    import json

    servers = {}
    ref_provider = dig(cfg, "references", "provider")
    db_backend = dig(cfg, "database", "backend")

    if ref_provider == "zotero":
        servers["zotero"] = {
            "command": "uvx",
            "args": ["--from", "zotero-mcp", "zotero-mcp"],
            "env": {
                "ZOTERO_LOCAL": "false",
                "ZOTERO_API_KEY": "${ZOTERO_API_KEY}",
                "ZOTERO_LIBRARY_ID": dig(cfg, "references", "zotero", "user_id") or "${ZOTERO_LIBRARY_ID}",
            },
        }
    if db_backend in ("directus-local", "managed"):
        servers["directus"] = {
            "type": "http",
            "url": "${DIRECTUS_URL}",
            "headers": {"Authorization": "Bearer ${DIRECTUS_TOKEN}"},
        }

    out = {"mcpServers": servers}
    target = PROJECT_ROOT / ".mcp.json"
    target.write_text(json.dumps(out, indent=2) + "\n")
    return str(target.relative_to(PROJECT_ROOT))


def render_protected_paths(cfg: dict) -> str | None:
    """Write the pre-write safety guard's protected-prefix list from config."""
    protected = dig(cfg, "paths", "protected_write_paths", default=[]) or []
    out = PROJECT_ROOT / ".claude" / "hooks" / "protected_paths.txt"
    header = "# Auto-generated from research-config.yml (paths.protected_write_paths).\n"
    header += "# One path prefix per line. Writes starting with any line are blocked.\n"
    out.write_text(header + "\n".join(protected) + ("\n" if protected else ""))
    return str(out.relative_to(PROJECT_ROOT))


def main() -> None:
    cfg = load_config()
    tokens = build_tokens(cfg)
    rendered = render_template_files(tokens)
    mcp = render_mcp(cfg, tokens)
    if mcp:
        rendered.append(mcp)
    rendered.append(render_protected_paths(cfg))

    print("Rendered:")
    for r in sorted(rendered):
        print(f"  ✓ {r}")
    print(f"\nMemory slug: {tokens['MEMORY_SLUG']}")
    print("Config applied. Edit research-config.yml and re-run ./setup.sh to change.")


if __name__ == "__main__":
    main()
