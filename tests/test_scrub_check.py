"""scripts/setup/scrub_check.py: clean tree passes, planted private path fails."""
from __future__ import annotations

import shutil
import subprocess
import sys

from conftest import REPO_ROOT


def _run_scrub(project):
    return subprocess.run(
        [sys.executable, str(project / "scripts" / "setup" / "scrub_check.py")],
        capture_output=True,
        text=True,
    )


def test_scrub_check_clean_then_planted_path(tmp_path):
    project = tmp_path / "my project"
    (project / "scripts" / "setup").mkdir(parents=True)
    shutil.copy(
        REPO_ROOT / "scripts" / "setup" / "scrub_check.py",
        project / "scripts" / "setup" / "scrub_check.py",
    )
    (project / "notes.md").write_text("Nothing private here.\n")

    clean = _run_scrub(project)
    assert clean.returncode == 0, clean.stdout + clean.stderr

    # Built by concatenation so this source file stays clean under scrub_check.
    private = "/" + "Users" + "/alice/Documents/data.csv"
    (project / "notes.md").write_text(f"See {private}\n")
    dirty = _run_scrub(project)
    assert dirty.returncode == 1
    assert "absolute user home path" in dirty.stdout
