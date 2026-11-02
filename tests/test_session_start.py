"""SessionStart hook: Pinned Anchors block re-injected after compaction."""
from __future__ import annotations

import subprocess

import pytest

from conftest import REPO_ROOT

HOOK = REPO_ROOT / ".claude" / "hooks" / "session-start-learnings.py"


@pytest.fixture
def project(scaffold_project):
    (scaffold_project / ".current_paper").write_text("example-paper\n")
    return scaffold_project


def _git(root, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=root, check=True, capture_output=True,
    )


def _run(run_hook, root, event, tmp_path):
    # HOME is redirected so the hook never reads the live machine's memory dir.
    env = {"CLAUDE_PROJECT_DIR": str(root), "HOME": str(tmp_path / "home")}
    return run_hook(HOOK, event, env)


def _context(res):
    assert res.returncode == 0
    return (res.json or {}).get("additionalContext", "")


def test_compact_pins_paper_and_latest_freeze(project, run_hook, tmp_path):
    _git(project, "init", "-q")
    _git(project, "add", "-A")
    _git(project, "commit", "-q", "-m", "init")
    _git(project, "tag", "example-paper-gold-v1")
    _git(project, "tag", "example-paper-gold-v2")
    ctx = _context(_run(run_hook, project, {"source": "compact"}, tmp_path))
    assert "Pinned Anchors" in ctx
    assert "example-paper" in ctx
    assert "**Phase:** 1" in ctx
    assert "example-paper-gold-v2" in ctx
    assert "example-paper-gold-v1" not in ctx


def test_startup_output_matches_no_source(project, run_hook, tmp_path):
    startup = _run(run_hook, project, {"source": "startup"}, tmp_path)
    none = _run(run_hook, project, {}, tmp_path)
    assert startup.stdout == none.stdout
    assert "Pinned Anchors" not in startup.stdout


def test_compact_without_current_paper(project, run_hook, tmp_path):
    (project / ".current_paper").unlink()
    res = _run(run_hook, project, {"source": "compact"}, tmp_path)
    assert res.returncode == 0
    assert "Pinned Anchors" not in res.stdout


def test_author_decisions_listed_and_capped(project, run_hook, tmp_path):
    notes = project / "papers" / "example-paper" / "extra.md"
    notes.write_text(
        "\n".join(f"AUTHOR DECISION: choice number {i}" for i in range(1, 10)) + "\n"
    )
    ctx = _context(_run(run_hook, project, {"source": "compact"}, tmp_path))
    assert "papers/example-paper/extra.md:1" in ctx
    assert "choice number 1" in ctx
    assert "choice number 8" in ctx
    assert "choice number 9" not in ctx
