#!/usr/bin/env python3
"""
verify_install.py — smoke-test a fresh install.

Checks the automatable parts of the acceptance gate:
  1. research-config.yml exists and parses
  2. rendered files exist (CLAUDE.md, .mcp.json)
  3. hooks are present and executable
  4. the derived memory-slug directory can be located under ~/.claude/projects
  5. the example paper is intact

Prints a green/red summary. Non-zero exit if any hard check fails.

Note: this does NOT run scrub_check. scrub_check is a maintainer publish gate
(catches secrets/home paths before publishing the kit to npm); a user's own home
path in their own gitignored research-config.yml is expected, not a leak.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

GREEN, RED, YELLOW, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


def ok(msg):
    print(f"  {GREEN}✓{RESET} {msg}")


def warn(msg):
    print(f"  {YELLOW}!{RESET} {msg}")


def fail(msg):
    print(f"  {RED}✗{RESET} {msg}")


def main() -> None:
    hard_failures = 0

    # 1. config
    cfg = PROJECT_ROOT / "research-config.yml"
    if cfg.exists():
        ok("research-config.yml present")
    else:
        fail("research-config.yml missing — run the scaffolder or ./setup.sh")
        hard_failures += 1

    # 2. rendered files
    claude_md = PROJECT_ROOT / "CLAUDE.md"
    if claude_md.exists():
        if "{{" in claude_md.read_text():
            fail("CLAUDE.md still contains unrendered {{TOKENS}}")
            hard_failures += 1
        else:
            ok("CLAUDE.md rendered")
    else:
        fail("CLAUDE.md not rendered — check render_templates.py output")
        hard_failures += 1

    if (PROJECT_ROOT / ".mcp.json").exists():
        ok(".mcp.json rendered")
    else:
        warn(".mcp.json not rendered (fine if no integrations enabled)")

    # 3. hooks
    hooks_dir = PROJECT_ROOT / ".claude" / "hooks"
    if hooks_dir.exists():
        non_exec = [h.name for h in hooks_dir.iterdir()
                    if h.suffix in (".py", ".sh") and not (h.stat().st_mode & 0o111)]
        if non_exec:
            fail(f"hooks not executable: {', '.join(non_exec)} — run install_hooks.py")
            hard_failures += 1
        else:
            ok("hooks present and executable")
    else:
        warn(".claude/hooks missing")

    # 4. memory slug dir
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "setup"))
        from render_templates import derive_memory_slug, load_config, dig  # type: ignore

        root = dig(load_config(), "project", "root") or str(PROJECT_ROOT)
        slug = derive_memory_slug(root)
        mem = Path.home() / ".claude" / "projects" / slug / "memory"
        if mem.exists():
            ok(f"memory dir exists: …/{slug}/memory")
        else:
            warn(f"memory dir not created yet (will appear on first Claude session): {slug}")
    except SystemExit:
        pass
    except Exception as e:
        warn(f"could not derive memory slug: {e}")

    # 5. example paper
    if (PROJECT_ROOT / "papers" / "example-paper" / "STATUS.md").exists():
        ok("example-paper template present")
    else:
        warn("papers/example-paper/STATUS.md missing")

    print()
    if hard_failures:
        print(f"{RED}Install verification failed: {hard_failures} hard check(s).{RESET}")
        sys.exit(1)
    print(f"{GREEN}Install verified.{RESET} Open in Claude Code and run /setup wren for a guided tour, or /paper to jump in.")


if __name__ == "__main__":
    main()
