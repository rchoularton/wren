"""Shared pytest fixtures: a hook runner and a realistic scaffolded project."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


class HookResult(NamedTuple):
    returncode: int
    stdout: str
    stderr: str
    json: dict | None  # parsed stdout when it is a JSON object, else None


def _run_hook(path, event: dict, env: dict | None = None) -> HookResult:
    """Run a hook as a subprocess with `event` as JSON on stdin.

    `.py` hooks run under the current interpreter, `.sh` hooks under bash.
    `env` entries are layered over the current environment (e.g. pass
    `{"CLAUDE_PROJECT_DIR": str(root)}` to point the hook at a project).
    """
    path = Path(path)
    if path.suffix == ".py":
        cmd = [sys.executable, str(path)]
    elif path.suffix == ".sh":
        cmd = ["bash", str(path)]
    else:
        raise ValueError(f"unsupported hook type: {path.suffix!r}")
    proc = subprocess.run(
        cmd,
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
        timeout=30,
    )
    parsed = None
    if proc.stdout.strip():
        try:
            candidate = json.loads(proc.stdout)
            parsed = candidate if isinstance(candidate, dict) else None
        except json.JSONDecodeError:
            pass
    return HookResult(proc.returncode, proc.stdout, proc.stderr, parsed)


@pytest.fixture
def run_hook():
    """Fixture returning `run_hook(path, event, env=None) -> HookResult`."""
    return _run_hook


@pytest.fixture
def scaffold_project(tmp_path) -> Path:
    """A temp project root (path contains a space) that looks like a scaffold.

    Copies `papers/example-paper`, `.claude/` and a rendered
    `research-config.yml`; hooks should be run with
    `CLAUDE_PROJECT_DIR=<returned root>`.
    """
    root = tmp_path / "my project"
    root.mkdir()
    ignore = shutil.ignore_patterns(
        "__pycache__", "*.pyc", "settings.local.json", "protected_paths.txt"
    )
    shutil.copytree(REPO_ROOT / ".claude", root / ".claude", ignore=ignore)
    shutil.copytree(
        REPO_ROOT / "papers" / "example-paper",
        root / "papers" / "example-paper",
        ignore=ignore,
    )
    # The example config is the default-valued form of the rendered config.
    shutil.copy(REPO_ROOT / "research-config.example.yml", root / "research-config.yml")
    return root
