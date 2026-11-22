"""Every sub-agent file has well-formed frontmatter; the librarian agents are read-only on the library."""
from __future__ import annotations

import re

import pytest
from conftest import REPO_ROOT

AGENTS = REPO_ROOT / ".claude" / "agents"
FILES = sorted(p for p in AGENTS.glob("*.md") if p.name != "README.md")
ALIASES = {"opus", "sonnet", "haiku"}  # .claude/lib/model-policy.mjs ALIASES
LIBRARIANS = ["librarian-cataloguer", "librarian-scout"]
# Read tools confirmed in the zotero-mcp docs (docs/tools.md). Explicit list: anything else fails.
ALLOWED_MCP = {
    "mcp__zotero__zotero_search_items",
    "mcp__zotero__zotero_get_item_metadata",
    "mcp__zotero__zotero_get_recent",
    "mcp__zotero__zotero_get_tags",
    "mcp__zotero__zotero_get_collections",
    "mcp__zotero__zotero_search_collections",
}
SCOUT_MCP = {"mcp__zotero__zotero_search_items", "mcp__zotero__zotero_get_item_metadata"}


def frontmatter(path):
    m = re.match(r"^---\n(.*?)\n---\n", path.read_text(), re.S)
    assert m, f"{path.name}: no frontmatter"
    fm = {}
    keys = [line.partition(':')[0] for line in m.group(1).split('\n')]
    dupes = {k for k in keys if keys.count(k) > 1}
    assert not dupes, f"{path.name}: duplicated frontmatter key(s) {dupes}"
    for line in m.group(1).split("\n"):
        k, sep, v = line.partition(":")
        assert sep and re.match(r"^[A-Za-z_]+$", k), f"{path.name}: unparseable frontmatter line {line!r}"
        v = v.split(" #")[0].strip() if not v.strip().startswith('"') else v.strip()
        fm[k] = v[1:-1] if len(v) > 1 and v[0] == v[-1] == '"' else v
    return fm


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_frontmatter(path):
    fm = frontmatter(path)
    assert fm["name"] == path.stem
    assert fm.get("description"), "description missing"
    assert fm["model"] in ALIASES


@pytest.mark.parametrize("name", LIBRARIANS)
def test_librarian_read_only(name):
    fm = frontmatter(AGENTS / f"{name}.md")
    assert "tools" in fm, "tools allowlist required"
    tools = [t.strip() for t in fm["tools"].split(",")]
    for banned in ("Bash", "Edit", "NotebookEdit"):
        assert banned not in tools
    assert "*" not in tools and all(t for t in tools)
    assert len(tools) == len(set(tools)), "duplicate tool in tools:"
    mcp = {t for t in tools if t.startswith("mcp__")}
    assert mcp <= ALLOWED_MCP, f"unlisted mcp tool(s): {mcp - ALLOWED_MCP}"
    if name == "librarian-scout":
        assert mcp <= SCOUT_MCP
    assert len(fm["description"]) <= 160
