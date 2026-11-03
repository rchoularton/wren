"""wren_status.py (npm run status) and papers_table.py (npm run papers:table)."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from conftest import REPO_ROOT

STATUS = REPO_ROOT / "scripts" / "utils" / "wren_status.py"
TABLE = REPO_ROOT / "scripts" / "utils" / "papers_table.py"


def _run(script, root, *args):
    return subprocess.run([sys.executable, str(script), "--repo", str(root), *args],
                          capture_output=True, text=True, timeout=30)


def _add_paper(root, pid, tier, nxt="", frontmatter=True):
    d = root / "papers" / pid
    d.mkdir()
    fm = (f'---\npaper_id: {pid}\ntitle: "Paper {pid}"\njournal: "J"\nphase: 3\n'
          f'tier: {tier}\nstatus: analysis\nnext: "{nxt}"\n---\n') if frontmatter else ""
    (d / "STATUS.md").write_text(fm + "# Status\n")


def _json(root):
    res = _run(STATUS, root, "--json", "--today", "2026-11-03")
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def _log(root, name, body):
    logs = root / "outputs" / "_logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / name).write_text(body)


@pytest.fixture
def project(scaffold_project):
    (scaffold_project / "papers" / "README.md").write_text(
        "# Papers\n\n<!-- papers:begin -->\n<!-- papers:end -->\n")
    return scaffold_project


def test_summary_lists_example_paper_and_marks_active(project):
    (project / ".current_paper").write_text("example-paper\n")
    out = _run(STATUS, project).stdout
    assert "▶ **example-paper**" in out
    assert "phase 1" in out


def test_tier_one_sorts_first_with_next_text(project):
    _add_paper(project, "urgent", 1, "Run the robustness checks")
    out = _run(STATUS, project).stdout
    assert out.index("urgent") < out.index("example-paper")
    assert "Run the robustness checks" in out


def test_status_without_frontmatter_is_unparsed(project):
    _add_paper(project, "bare", 1, frontmatter=False)
    res = _run(STATUS, project)
    assert res.returncode == 0
    assert "Unparsed" in res.stdout and "bare" in res.stdout
    assert _json(project)["unparsed"] == ["bare"]


def test_job_verdicts_from_logs(project):
    _log(project, "digest_2026-10-01.log", "start\nfinished: done\n")
    _log(project, "audit_2026-11-02.log", "start\nTraceback (most recent call last)\n")
    _log(project, "wren.digest.out.log", "ignored\n")
    jobs = {j["key"]: j for j in _json(project)["jobs"]}
    assert set(jobs) == {"digest", "audit"}
    assert jobs["digest"]["verdict"] == "ok" and jobs["digest"]["overdue"]
    assert jobs["audit"]["verdict"] == "failed" and not jobs["audit"]["overdue"]


def test_no_logs_says_no_scheduled_jobs(project):
    assert "no scheduled jobs have run" in _run(STATUS, project).stdout
    assert _json(project)["jobs"] == []


def test_papers_table_writes_and_is_idempotent(project):
    readme = project / "papers" / "README.md"
    assert _run(TABLE, project).returncode == 0
    first = readme.read_bytes()
    assert b"`example-paper`" in first
    assert _run(TABLE, project).returncode == 0
    assert readme.read_bytes() == first


def test_missing_papers_dir_exits_2(tmp_path):
    res = _run(STATUS, tmp_path)
    assert res.returncode == 2
    assert "papers/" in res.stderr
