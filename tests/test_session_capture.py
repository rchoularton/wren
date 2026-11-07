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


HELP = ('if [[ "$1" == "--help" ]]; then echo "--tools --setting-sources '
        '--strict-mcp-config --no-session-persistence"; exit 0; fi\n')


def fake_claude(tmp_path, body, rc=0):
    f = tmp_path / "fake-claude"
    f.write_text(f"#!/bin/bash\n{HELP}cat >/dev/null\n{body}\nexit {rc}\n")
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
        f'#!/bin/bash\n{HELP}wc -c > {seen}.size\necho "$WREN_CAPTURE_HOOK" > {seen}.env\n'
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


# --- privacy-review follow-ups ------------------------------------------------

import importlib.util  # noqa: E402


def load_capture():
    spec = importlib.util.spec_from_file_location("capture_session", CAPTURE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_argv_is_sandboxed(monkeypatch):
    cap = load_capture()
    calls = {}

    class P:
        pid = 1
        returncode = 0
        def communicate(self, *a, **k):
            return "- ok", ""

    monkeypatch.setattr(cap.subprocess, "run", lambda argv, **k: type(
        "R", (), {"stdout": " ".join(cap.REQUIRED_FLAGS), "stderr": ""})())
    def popen(argv, **k):
        calls["argv"], calls["kw"] = argv, k
        return P()
    monkeypatch.setattr(cap.subprocess, "Popen", popen)
    assert cap.summarize("u" * 200, "a" * 200, "/fake/claude") == "- ok"
    argv = calls["argv"]
    assert argv[argv.index("--tools") + 1] == ""
    assert argv[argv.index("--setting-sources") + 1] == ""
    assert "--strict-mcp-config" in argv and "--no-session-persistence" in argv
    assert calls["kw"]["start_new_session"] is True


def test_missing_sandbox_flag_captures_nothing(env, tmp_path):
    claude = tmp_path / "old-claude"
    claude.write_text('#!/bin/bash\nif [[ "$1" == "--help" ]]; then echo "--model"; exit 0; fi\n'
                      'touch ' + str(tmp_path / "ran") + '\necho "- x"\n')
    claude.chmod(0o755)
    assert run_capture(env, tmp_path, claude).returncode == 0
    assert not (tmp_path / "ran").exists()
    assert not (env["sessions"] / f"{TODAY}.md").exists()
    assert "lacks sandbox flags" in (env["sessions"] / ".capture_errors.log").read_text()


def test_parallel_helpers_write_one_entry(env, tmp_path):
    claude = fake_claude(tmp_path, "sleep 1\n" + BULLETS)
    t = transcript(tmp_path)
    e = {**os.environ, **env["env"], "WREN_CLAUDE_BIN": str(claude)}
    procs = [subprocess.Popen([sys.executable, str(CAPTURE), str(t), "sess1234abcd"], env=e)
             for _ in range(2)]
    assert [p.wait(timeout=30) for p in procs] == [0, 0]
    text = (env["sessions"] / f"{TODAY}.md").read_text()
    assert text.count("(auto-captured)") == 1
    assert len((env["sessions"] / ".captured").read_text().split()) == 1
    assert not list(env["sessions"].glob(".lock-*"))


def test_timeout_kills_process_group(tmp_path, monkeypatch):
    cap = load_capture()
    monkeypatch.setattr(cap, "CLAUDE_TIMEOUT_S", 1)
    pidfile = tmp_path / "child.pid"
    script = tmp_path / "slow"
    script.write_text(f"#!/bin/bash\nsleep 30 &\necho $! > {pidfile}\nwait\n")
    script.chmod(0o755)
    with pytest.raises(subprocess.TimeoutExpired):
        cap.run_bounded([str(script)], "x", dict(os.environ))
    pid = int(pidfile.read_text())
    time.sleep(0.3)
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


FALSE_POSITIVES = {
    "block_scalar": "tiers:\n  research_memory: true\n  note: |\n    session_capture: true\n",
    "nested": "tiers:\n  research_memory:\n    session_capture: true\n",
}


@pytest.mark.parametrize("case", FALSE_POSITIVES)
def test_toggle_ignores_nested_key(env, run_hook, tmp_path, case):
    (env["root"] / "research-config.yml").write_text(FALSE_POSITIVES[case])
    claude = fake_claude(tmp_path, BULLETS)
    run_hook(STOP, {"transcript_path": str(transcript(tmp_path)), "session_id": "s"},
             {**env["env"], "WREN_CLAUDE_BIN": str(claude)})
    _plant_bullets(env)
    time.sleep(0.5)
    assert not (env["sessions"] / ".captured").exists()
    assert "Recent sessions" not in _ctx(run_hook(START, {}, env["env"]))


def test_toggle_direct_child_is_honoured(env, run_hook):
    (env["root"] / "research-config.yml").write_text(
        "tiers:\n  research_memory: true\n  session_capture: true  # on\nother:\n  x: 1\n")
    _plant_bullets(env)
    assert "Recent sessions" in _ctx(run_hook(START, {}, env["env"]))


def test_recall_terms_are_fixed_strings(env):
    env["sessions"].mkdir(parents=True)
    (env["sessions"] / "2026-11-01.md").write_text(
        "### 09:12 - session s\n- Called f(x) twice.\n- Budget was $5.\n- Plain note\n")
    run = lambda *a: subprocess.run(
        ["bash", str(RECALL), *a], capture_output=True, text=True, timeout=30,
        env={**os.environ, "WREN_MEMORY_DIR": str(env["mem"])})
    assert "Called f(x)" in run("f(x)").stdout
    assert "Budget was $5" in run("$5").stdout
    dot = run(".")  # literal dot: matches the bullets that contain one, not everything
    assert "Plain note" not in dot.stdout and "Called f(x)" in dot.stdout
    empty = run("")
    assert empty.returncode == 2 and "usage" in empty.stderr


def test_stop_hook_path_with_space_dispatches(env, run_hook, tmp_path):
    set_toggle(env["root"], "true")
    d = tmp_path / "dir with space"
    d.mkdir()
    t = transcript(d)
    claude = fake_claude(tmp_path, BULLETS)
    res = run_hook(STOP, {"transcript_path": str(t), "session_id": "sess1234abcd"},
                   {**env["env"], "WREN_CLAUDE_BIN": str(claude)})
    assert res.returncode == 0
    log = env["sessions"] / f"{TODAY}.md"
    for _ in range(50):
        if log.exists():
            break
        time.sleep(0.1)
    assert "Model B was chosen" in log.read_text()


def test_stop_hook_on_path_is_fast(env, run_hook, tmp_path):
    set_toggle(env["root"], "true")
    claude = fake_claude(tmp_path, "sleep 2\n" + BULLETS)
    start = time.monotonic()
    res = run_hook(STOP, {"transcript_path": str(transcript(tmp_path)), "session_id": "s"},
                   {**env["env"], "WREN_CLAUDE_BIN": str(claude)})
    assert res.returncode == 0 and time.monotonic() - start < 1.0
