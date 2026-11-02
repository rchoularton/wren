"""Proof tests for the harness, against hooks that already exist."""
from __future__ import annotations


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
