"""scripts/audit/check_model_policy_drift.py: clean copy passes; stale id / unknown alias fail."""
from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

from conftest import REPO_ROOT


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "my project"
    (root / "scripts" / "audit").mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "scripts" / "audit" / "check_model_policy_drift.py",
        root / "scripts" / "audit" / "check_model_policy_drift.py",
    )
    shutil.copytree(
        REPO_ROOT / ".claude" / "lib", root / ".claude" / "lib",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    shutil.copytree(
        REPO_ROOT / ".claude" / "agents", root / ".claude" / "agents",
    )
    return root


def _run(root):
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "audit" / "check_model_policy_drift.py")],
        capture_output=True,
        text=True,
    )


def test_clean_copy_passes(project):
    r = _run(project)
    assert r.returncode == 0, r.stdout + r.stderr


def test_planted_stale_id_fails(project):
    (project / "README.md").write_text("Uses claude-haiku-4-5-20251001 for triage.\n")
    r = _run(project)
    assert r.returncode == 1
    assert "claude-haiku-4-5-20251001" in r.stdout


def test_planted_unknown_alias_fails(project):
    agent = project / ".claude" / "agents" / "qc-skeptic.md"
    agent.write_text(agent.read_text().replace("model: opus", "model: gpt-9", 1))
    r = _run(project)
    assert r.returncode == 1
    assert "qc-skeptic.md" in r.stdout and "gpt-9" in r.stdout
