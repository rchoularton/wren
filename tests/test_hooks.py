"""Proof tests for the harness, against hooks that already exist."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

from conftest import REPO_ROOT


def _write_event(path) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": "x"}}


def test_safety_guard_blocks_protected_and_allows_elsewhere(run_hook, scaffold_project):
    root = scaffold_project
    protected = root / "protected zone"
    (root / ".claude" / "hooks" / "protected_paths.txt").write_text(f"{protected}\n")
    hook = root / ".claude" / "hooks" / "pre-write-safety-guard.sh"
    env = {"CLAUDE_PROJECT_DIR": str(root)}

    denied = run_hook(hook, _write_event(protected / "paper.docx"), env)
    assert denied.returncode == 0
    assert denied.json["decision"] == "block"

    allowed = run_hook(hook, _write_event(root / "outputs" / "fine.txt"), env)
    assert allowed.returncode == 0
    assert allowed.json == {"decision": "approve"}


def test_outputs_manifest_flags_unregistered_dir(run_hook, scaffold_project):
    root = scaffold_project
    outputs = root / "outputs"
    outputs.mkdir()
    (outputs / "MANIFEST.md").write_text("| `registered/` | current | x | y |\n")
    hook = root / ".claude" / "hooks" / "post-write-outputs-manifest.py"
    env = {"CLAUDE_PROJECT_DIR": str(root)}

    new = run_hook(hook, _write_event(outputs / "new_analysis" / "r.csv"), env)
    assert new.returncode == 0
    assert "new_analysis/" in new.json["systemMessage"]

    known = run_hook(hook, _write_event(outputs / "registered" / "r.csv"), env)
    assert known.returncode == 0
    assert known.json == {}


ADVISORY = REPO_ROOT / ".claude" / "hooks" / "pre-task-model-advisory.py"
PROMPT_HOOK = REPO_ROOT / ".claude" / "hooks" / "user-prompt-paper-context.py"


def _agent_event(tool="Agent", **tool_input) -> dict:
    return {"tool_name": tool, "tool_input": tool_input}


def test_advisory_reminds_when_explore_has_no_model(run_hook):
    for tool in ("Agent", "Task"):
        res = run_hook(ADVISORY, _agent_event(tool, subagent_type="Explore"))
        assert res.returncode == 0
        out = res.json["hookSpecificOutput"]
        assert out["hookEventName"] == "PreToolUse"
        assert "sonnet" in out["additionalContext"]
        assert "permissionDecision" not in out


def test_advisory_silent_when_model_pinned(run_hook):
    res = run_hook(ADVISORY, _agent_event(subagent_type="Explore", model="sonnet"))
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_advisory_silent_for_non_inheriting_agent(run_hook):
    res = run_hook(ADVISORY, _agent_event(subagent_type="peer-reviewer-methods"))
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_advisory_fails_open_on_malformed_stdin():
    proc = subprocess.run(
        [sys.executable, str(ADVISORY)], input="not json {", capture_output=True, text=True, timeout=30
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_prompt_hook_does_not_block_on_open_stdin(tmp_path):
    proc = subprocess.Popen(
        [sys.executable, str(PROMPT_HOOK)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)},
    )
    try:  # stdin pipe is deliberately never written to or closed
        start = time.monotonic()
        out, _ = proc.communicate(timeout=2)
        assert time.monotonic() - start < 2
        assert proc.returncode == 0
        assert json.loads(out) == {}
    finally:
        proc.kill()
        proc.wait()
