"""wren_status.py (npm run status) and papers_table.py (npm run papers:table)."""
from __future__ import annotations

import json
import os
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
    assert _json(project)["unparsed"] == ["bare (no frontmatter)"]


def test_job_verdicts_from_end_markers(project):
    _log(project, "digest_2026-10-01.log", "start\n=== WREN_JOB_END exit=0 ===\n")
    _log(project, "audit_2026-11-02.log", "start\nall fine\n=== WREN_JOB_END exit=3 ===\n")
    _log(project, "wren.digest.out.log", "ignored\n")
    jobs = {j["key"]: j for j in _json(project)["jobs"]}
    assert set(jobs) == {"digest", "audit"}
    assert jobs["digest"]["verdict"] == "ok" and jobs["digest"]["overdue"]
    assert jobs["audit"]["verdict"] == "failed" and not jobs["audit"]["overdue"]


@pytest.mark.parametrize("last,expected", [
    ("0 errors, done", "ok"),
    ("Failures: 0. Completed.", "ok"),
    ("Traceback (most recent call last)", "failed"),
    ("Job failed: not completed", "unknown"),
    ("no errors in the citations", "unknown"),
    ("ERROR: upstream refused", "failed"),
    ("nothing to say", "unknown"),
])
def test_keyword_fallback_without_marker(project, last, expected):
    _log(project, "job_2026-11-02.log", f"start\n{last}\n\n")
    assert _json(project)["jobs"][0]["verdict"] == expected


def test_marker_found_beyond_twenty_lines(project):
    body = "=== WREN_JOB_END exit=1 ===\n" + "".join(f"line {i}\n" for i in range(29)) + "done\n"
    _log(project, "job_2026-11-02.log", body)
    assert _json(project)["jobs"][0]["verdict"] == "failed"


def test_marker_beats_keywords(project):
    _log(project, "job_2026-11-02.log", "0 errors, done\n=== WREN_JOB_END exit=1 ===\n")
    assert _json(project)["jobs"][0]["verdict"] == "failed"


def test_no_logs_says_no_scheduled_jobs(project):
    assert "no scheduled jobs have run" in _run(STATUS, project).stdout
    assert _json(project)["jobs"] == []


def test_papers_table_writes_and_is_idempotent(project):
    readme = project / "papers" / "README.md"
    prose = "# Papers\n\nFirst paragraph.\n\nSecond paragraph.\n\n"
    after = "\n\nTrailing prose.\n"
    readme.write_text(f"{prose}<!-- papers:begin -->\n<!-- papers:end -->{after}")
    _add_paper(project, "pipe", 1)
    s = project / "papers" / "pipe" / "STATUS.md"
    s.write_text(s.read_text().replace('"Paper pipe"', '"A | B"'))
    assert _run(TABLE, project).returncode == 0
    first = readme.read_bytes().decode()
    assert first.startswith(prose) and first.endswith(after)
    assert "A \\| B" in first and "`example-paper`" in first
    assert _run(TABLE, project).returncode == 0
    assert readme.read_bytes().decode() == first


def test_papers_table_keeps_crlf(project):
    readme = project / "papers" / "README.md"
    readme.write_bytes(b"# Papers\r\n\r\n<!-- papers:begin -->\r\n<!-- papers:end -->\r\nend\r\n")
    assert _run(TABLE, project).returncode == 0
    data = readme.read_bytes()
    assert b"\n" not in data.replace(b"\r\n", b"")
    assert b"`example-paper`" in data
    assert _run(TABLE, project).stdout.startswith("papers table already")


@pytest.mark.skipif(sys.platform == "win32", reason="chmod semantics")
def test_unreadable_status_is_unparsed(project):
    _add_paper(project, "locked", 1)
    path = project / "papers" / "locked" / "STATUS.md"
    path.chmod(0)
    try:
        res = _run(STATUS, project)
        if os.access(path, os.R_OK):
            pytest.skip("running as a user that ignores file modes")
        assert res.returncode == 0
        assert "locked (unreadable" in res.stdout
    finally:
        path.chmod(0o644)


def test_dir_without_status_and_missing_active_paper(project):
    (project / "papers" / "empty").mkdir()
    (project / ".current_paper").write_text("ghost\n")
    rep = _json(project)
    assert "empty (no STATUS.md)" in rep["unparsed"]
    assert len(rep["warnings"]) == 1 and "ghost" in rep["warnings"][0]
    assert not any(p["active"] for p in rep["papers"])
    assert "Warning: " in _run(STATUS, project).stdout


def test_json_generated_is_reproducible(project):
    assert _json(project)["generated"] == "2026-11-03"


def test_summary_is_capped(project):
    for i in range(30):
        _add_paper(project, f"p{i:02d}", 2 if i else 1)
    (project / ".current_paper").write_text("p29\n")
    out = _run(STATUS, project).stdout
    assert len(out.splitlines()) < 30
    assert "more (use --full)" in out and "▶ **p29**" in out


def test_missing_papers_dir_exits_2(tmp_path):
    res = _run(STATUS, tmp_path)
    assert res.returncode == 2
    assert "papers/" in res.stderr
