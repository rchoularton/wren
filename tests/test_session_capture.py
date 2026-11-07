"""Opt-in session capture (#25): Stop hook, capture helper, recall, injection."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

import pytest

from conftest import REPO_ROOT

STOP = REPO_ROOT / ".claude" / "hooks" / "stop-session-capture.sh"
CAPTURE = REPO_ROOT / ".claude" / "hooks" / "capture_session.py"
START = REPO_ROOT / ".claude" / "hooks" / "session-start-learnings.py"
RECALL = REPO_ROOT / "scripts" / "utils" / "recall_context.sh"
TODAY = datetime.now().strftime("%Y-%m-%d")


def set_toggle(root, value):
    cfg = root / "research-config.yml"
    text = cfg.read_text()
    text = re.sub(r"^\s*session_capture:.*\n", "", text, flags=re.M)
    if value is not None:
        text = text.rstrip("\n") + f"\n  session_capture: {value}\n"
    cfg.write_text(text)


@pytest.fixture
def env(scaffold_project, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    slug = re.sub(r"[/.]", "-", str(scaffold_project.resolve()))
    mem = home / ".claude" / "projects" / slug / "memory"
    return {
        "root": scaffold_project, "home": home, "mem": mem,
        "sessions": mem / "context" / "sessions",
        "env": {"CLAUDE_PROJECT_DIR": str(scaffold_project), "HOME": str(home)},
    }


def transcript(tmp_path):
    p = tmp_path / "t.jsonl"
    events = [
        {"type": "user", "uuid": "u1", "message": {"content": "Please compare the two models. " * 10}},
        {"type": "assistant", "uuid": "a1", "message": {"content": [
            {"type": "text", "text": "I compared them and chose model B because it fits. " * 10}]}},
    ]
    p.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    return p


def fake_claude(tmp_path, body, rc=0):
    f = tmp_path / "fake-claude"
    f.write_text(f"#!/bin/bash\ncat >/dev/null\n{body}\nexit {rc}\n")
    f.chmod(0o755)
    return f


def run_capture(env, tmp_path, claude, extra=None):
    e = {**{k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"},
         **env["env"], "WREN_CLAUDE_BIN": str(claude), **(extra or {})}
    return subprocess.run(
        [sys.executable, str(CAPTURE), str(transcript(tmp_path)), "sess1234abcd"],
        capture_output=True, text=True, env=e, timeout=30)


BULLETS = "echo '- The user compared two models.'; echo '- Model B was chosen.'"


@pytest.mark.parametrize("value", [None, "false"])
def test_stop_hook_off_is_silent_and_fast(env, run_hook, tmp_path, value):
    set_toggle(env["root"], value)
    marker = tmp_path / "spawned"
    claude = fake_claude(tmp_path, f"touch {marker}")
    t = transcript(tmp_path)
    start = time.monotonic()
    res = run_hook(STOP, {"transcript_path": str(t), "session_id": "s"},
                   {**env["env"], "WREN_CLAUDE_BIN": str(claude)})
    elapsed = time.monotonic() - start
    time.sleep(0.5)
    assert res.returncode == 0 and res.stdout == "" and res.stderr == ""
    assert elapsed < 1.0
    assert not marker.exists() and not env["sessions"].exists()


def test_stop_hook_missing_config_is_off(env, run_hook, tmp_path):
    (env["root"] / "research-config.yml").unlink()
    res = run_hook(STOP, {"transcript_path": str(transcript(tmp_path))}, env["env"])
    assert res.returncode == 0 and res.stdout == ""


def test_stop_hook_guard_env_exits_immediately(env, run_hook, tmp_path):
    set_toggle(env["root"], "true")
    res = run_hook(STOP, {"transcript_path": str(transcript(tmp_path))},
                   {**env["env"], "WREN_CAPTURE_HOOK": "1"})
    assert res.returncode == 0 and res.stdout == ""
    time.sleep(0.3)
    assert not env["sessions"].exists()


def test_stop_hook_on_dispatches_detached_capture(env, run_hook, tmp_path):
    set_toggle(env["root"], "true")
    claude = fake_claude(tmp_path, BULLETS)
    res = run_hook(STOP, {"transcript_path": str(transcript(tmp_path)), "session_id": "sess1234abcd"},
                   {**env["env"], "WREN_CLAUDE_BIN": str(claude)})
    assert res.returncode == 0
    log = env["sessions"] / f"{TODAY}.md"
    for _ in range(50):
        if log.exists():
            break
        time.sleep(0.1)
    assert "Model B was chosen" in log.read_text()


def test_capture_writes_bullets_and_is_idempotent(env, tmp_path):
    claude = fake_claude(tmp_path, BULLETS)
    assert run_capture(env, tmp_path, claude).returncode == 0
    log = env["sessions"] / f"{TODAY}.md"
    text = log.read_text()
    assert "- The user compared two models." in text and "- Model B was chosen." in text
    hashes = (env["sessions"] / ".captured").read_text().split()
    assert len(hashes) == 1
    assert run_capture(env, tmp_path, claude).returncode == 0
    assert log.read_text() == text
    assert (env["sessions"] / ".captured").read_text().split() == hashes


def test_capture_failure_logs_and_writes_nothing(env, tmp_path):
    claude = fake_claude(tmp_path, "echo boom >&2", rc=3)
    assert run_capture(env, tmp_path, claude).returncode == 0
    assert not (env["sessions"] / f"{TODAY}.md").exists()
    lines = (env["sessions"] / ".capture_errors.log").read_text().splitlines()
    assert len(lines) == 1 and "rc=3" in lines[0]


def test_capture_without_claude_binary_is_silent(env, tmp_path):
    res = run_capture(env, tmp_path, tmp_path / "missing", {"PATH": "/usr/bin:/bin"})
    assert res.returncode == 0 and res.stdout == "" and not env["sessions"].exists()


def test_capture_sends_bounded_excerpt_with_guard_env(env, tmp_path):
    seen = tmp_path / "seen"
    claude = fake_claude(tmp_path, f'echo "$WREN_CAPTURE_HOOK" > {seen}.env; pwd > {seen}.cwd; echo "- ok"')
    # Rewrite so stdin is kept for size measurement.
    claude.write_text(
        f'#!/bin/bash\nwc -c > {seen}.size\necho "$WREN_CAPTURE_HOOK" > {seen}.env\n'
        f'pwd -P > {seen}.cwd\necho "- ok"\n')
    t = tmp_path / "big.jsonl"
    t.write_text("\n".join(json.dumps(e) for e in [
        {"type": "user", "uuid": "u", "message": {"content": "q " * 20000}},
        {"type": "assistant", "uuid": "a", "message": {"content": [{"type": "text", "text": "w " * 20000}]}},
    ]))
    e = {**os.environ, **env["env"], "WREN_CLAUDE_BIN": str(claude)}
    subprocess.run([sys.executable, str(CAPTURE), str(t), "s"], env=e, timeout=30, check=True)
    assert int(open(f"{seen}.size").read()) < 7500  # ~6,000 excerpt plus the fixed prompt
    assert open(f"{seen}.env").read().strip() == "1"
    assert open(f"{seen}.cwd").read().strip() == os.path.realpath(env["home"])


def test_recall_finds_term_with_date_heading(env):
    env["sessions"].mkdir(parents=True)
    (env["sessions"] / "2026-11-01.md").write_text(
        "# Session log\n\n### 09:12 - session ab12cd34 (auto-captured)\n"
        "- Chose the bootstrap method for intervals.\n- Left axis labels open.\n")
    run = lambda *a: subprocess.run(
        ["bash", str(RECALL), *a], capture_output=True, text=True, timeout=30,
        env={**os.environ, "WREN_MEMORY_DIR": str(env["mem"])})
    hit = run("BOOTSTRAP")
    assert hit.returncode == 0
    assert "[2026-11-01 | 09:12 - session ab12cd34 (auto-captured)]" in hit.stdout
    assert "bootstrap method" in hit.stdout and "axis labels" not in hit.stdout
    miss = run("zebra")
    assert miss.returncode == 1 and "nothing captured matches" in miss.stdout


def _plant_bullets(env, n=50):
    env["sessions"].mkdir(parents=True, exist_ok=True)
    (env["sessions"] / f"{TODAY}.md").write_text(
        "### 10:00 - session x (auto-captured)\n"
        + "".join(f"- Planted bullet number {i} " + "pad " * 40 + "\n" for i in range(n)))


def _ctx(res):
    assert res.returncode == 0
    return (res.json or {}).get("additionalContext", "")


@pytest.mark.parametrize("value", [None, "false"])
def test_injection_off(env, run_hook, value):
    set_toggle(env["root"], value)
    _plant_bullets(env)
    assert "Recent sessions" not in _ctx(run_hook(START, {}, env["env"]))


def test_injection_on_is_capped(env, run_hook):
    set_toggle(env["root"], "true")
    _plant_bullets(env)
    ctx = _ctx(run_hook(START, {}, env["env"]))
    assert "## Recent sessions" in ctx
    block = ctx[ctx.index("## Recent sessions"):]
    assert len(block.encode()) < 1200
    assert block.count("\n- ") <= 8
    assert "bullet number 49" in block  # newest kept


def test_context_size_default_total_and_optin_line():
    r = subprocess.run([sys.executable, str(REPO_ROOT / "scripts/utils/context_size.py"), "--json"],
                       capture_output=True, text=True, timeout=60, check=True)
    d = json.loads(r.stdout)
    assert d["total_bytes"] < 34_000  # default config: capture off, 0 bytes of sessions
    assert 0 < d["optin_session_capture_bytes"] <= 1200
    text = subprocess.run([sys.executable, str(REPO_ROOT / "scripts/utils/context_size.py")],
                          capture_output=True, text=True, timeout=60, check=True).stdout
    assert "with session_capture on: +" in text
