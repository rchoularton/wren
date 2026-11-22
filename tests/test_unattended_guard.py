"""The unattended-run boundary: .claude/hooks/pre-tool-unattended-guard.sh + unattended_guard.py. Offline."""
from __future__ import annotations

import json
import os

import pytest
from conftest import REPO_ROOT

SH = REPO_ROOT / ".claude" / "hooks" / "pre-tool-unattended-guard.sh"
PY = REPO_ROOT / ".claude" / "hooks" / "unattended_guard.py"
SAFETY = REPO_ROOT / ".claude" / "hooks" / "pre-write-safety-guard.sh"
D = "2026-11-22"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("WREN_UNATTENDED", raising=False)


@pytest.fixture
def proj(tmp_path):
    root = tmp_path / "proj"
    (root / "outputs" / "librarian").mkdir(parents=True)
    (root / "scripts" / "zotero").mkdir(parents=True)
    (root / "package.json").write_text("{}")
    return root


def call(run_hook, proj, tool, tool_input, active="1", hook=SH, raw=None):
    env = {"CLAUDE_PROJECT_DIR": str(proj)}
    if active is not None:
        env["WREN_UNATTENDED"] = active
    if raw is not None:
        import subprocess
        e = {**{k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}, **env}
        p = subprocess.run(["bash", str(hook)], input=raw, capture_output=True, text=True, env=e, timeout=30)
        return p.returncode, p.stdout, p.stderr
    r = run_hook(hook, {"tool_name": tool, "tool_input": tool_input}, env)
    return r.returncode, r.stdout, r.stderr


def denied(res):
    rc, out, err = res
    assert rc == 2, (rc, out, err)
    d = json.loads(out)["hookSpecificOutput"]
    assert d["hookEventName"] == "PreToolUse" and d["permissionDecision"] == "deny" and d["permissionDecisionReason"]
    assert err.strip()
    return d["permissionDecisionReason"]


def allowed(res):
    rc, out, err = res
    assert rc == 0 and out.strip() == "", (rc, out, err)


# --- inactive
@pytest.mark.parametrize("tool,inp", [
    ("Bash", {"command": "rm -rf x"}),
    ("Write", {"file_path": "/etc/passwd", "content": "x"}),
    ("Edit", {"file_path": "package.json"}),
    ("mcp__zotero__zotero_delete_item", {}),
])
def test_inactive_is_silent_for_everything(run_hook, proj, tool, inp):
    allowed(call(run_hook, proj, tool, inp, active=None))
    allowed(call(run_hook, proj, tool, inp, active=""))
    allowed(call(run_hook, proj, tool, inp, active="0"))


@pytest.mark.parametrize("value,active", [("1", True), ("true", True), ("yes", True), (" 1", True), ("on", True),
                                           ("0", False), ("false", False), ("no", False), ("", False), ("FALSE", False)])
def test_activation_values_fail_closed(run_hook, proj, value, active):
    res = call(run_hook, proj, "Bash", {"command": "cp a b"}, active=value)
    if active:
        denied(res)
    else:
        allowed(res)


# --- Bash
ALLOWED_BASH = [
    "date +%F",
    f"npm run zotero:duplicates -- --out outputs/librarian/duplicates_{D}.json --proposals outputs/librarian/duplicates_{D}.proposals.json",
    f"npm run zotero:duplicates -- --out outputs/librarian/duplicates_{D}.json --proposals outputs/librarian/duplicates_{D}.proposals.json --limit 500",
    f"npm run zotero:duplicates -- --out outputs/librarian/duplicates_{D}.json --proposals outputs/librarian/duplicates_{D}.proposals.json --limit 500 --no-fuzzy",
    f"npm run zotero:duplicates -- --out outputs/librarian/duplicates_{D}.json --proposals outputs/librarian/duplicates_{D}.proposals.json --no-fuzzy",
    f"npm run zotero:build-queue -- --date {D}",
    f"npm run zotero:queue -- status outputs/librarian/approval_queue_{D}.json",
    f"  npm run zotero:build-queue -- --date {D}  ",
]


@pytest.mark.parametrize("cmd", ALLOWED_BASH)
def test_allowed_bash_forms(run_hook, proj, cmd):
    allowed(call(run_hook, proj, "Bash", {"command": cmd}))


DENIED_BASH = [
    "npm run pdf:fill -- x --apply",
    "npm run zotero:queue -- approve 1 q.json",
    "npm run zotero:queue -- status q.json; node x",
    f"npm run zotero:queue -- status outputs/librarian/approval_queue_{D}.json; node x",
    "env -u WREN_UNATTENDED npm run zotero:queue -- skip 1 q",
    'python3 -c "print(1)"',
    "node scripts/zotero/approval-queue.mjs approve 1 q",
    f"npm run zotero:build-queue -- --date {D} --force",
    "npm run zotero:duplicates -- --out /tmp/x",
    f"npm run zotero:duplicates -- --out outputs/librarian/duplicates_{D}.json --proposals outputs/librarian/duplicates_2026-01-01.proposals.json",
    "date; rm -rf x",
    "cp a b",
    "date +%F\nrm x",
    "date +%F && ls",
    "date +%F | sh",
    "date +%F > f",
    "date $(id)",
    f"npm run zotero:queue -- status outputs/librarian/approval_queue_{D}.json `id`",
    "date +%F &",
]


@pytest.mark.parametrize("cmd", DENIED_BASH)
def test_denied_bash_forms(run_hook, proj, cmd):
    assert denied(call(run_hook, proj, "Bash", {"command": cmd})) == "unattended run: command not on the allowlist"


# --- Write
@pytest.mark.parametrize("name", [f"cataloguer_{D}.md", f"cataloguer_{D}.proposals.json", f"scout_{D}.md",
                                  f"scout_{D}.proposals.json", f"report_{D}.md"])
def test_write_allowed_for_the_five_files(run_hook, proj, name):
    allowed(call(run_hook, proj, "Write", {"file_path": str(proj / "outputs" / "librarian" / name), "content": "x"}))
    allowed(call(run_hook, proj, "Write", {"file_path": f"outputs/librarian/{name}", "content": "x"}))


def test_write_denied_elsewhere(run_hook, proj, tmp_path):
    lib = proj / "outputs" / "librarian"
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (lib / f"scout_{D}.md").symlink_to(outside / "target.md")
    (lib / "linkdir").symlink_to(outside)
    cases = [
        lib / f"approval_queue_{D}.json", lib / f"approval_queue_{D}.json.lock", lib / f"duplicates_{D}.json",
        lib / f"duplicates_{D}.proposals.json", lib / f"rejected_{D}.json", lib / "report_x.md",
        proj / "package.json", proj / "scripts" / "zotero" / "detect-duplicates.mjs", proj / ".claude" / "settings.json",
        lib / ".." / ".." / "x.md", lib / f"scout_{D}.md",  # symlink out of the directory
        lib / "linkdir" / f"scout_{D}-2.md", lib / "sub" / f"report_{D}.md",
        outside / f"report_{D}.md", tmp_path / "abs.md",
    ]
    for c in cases:
        denied(call(run_hook, proj, "Write", {"file_path": str(c), "content": "x"}))
    denied(call(run_hook, proj, "Write", {"file_path": f"outputs/librarian/../../x.md", "content": "x"}))
    denied(call(run_hook, proj, "Write", {"content": "x"}))


@pytest.mark.parametrize("tool", ["Edit", "MultiEdit", "NotebookEdit"])
def test_edit_tools_always_denied(run_hook, proj, tool):
    denied(call(run_hook, proj, tool, {"file_path": str(proj / "outputs" / "librarian" / f"report_{D}.md")}))


# --- MCP
@pytest.mark.parametrize("tool", ["mcp__zotero__zotero_search_items", "mcp__zotero__zotero_get_item_metadata", "mcp__zotero__zotero_get_recent",
                                  "mcp__zotero__zotero_get_tags", "mcp__zotero__zotero_get_collections", "mcp__zotero__zotero_search_collections",
                                  "mcp__claude_ai_Gmail__create_draft"])
def test_listed_mcp_tools_allowed(run_hook, proj, tool):
    allowed(call(run_hook, proj, tool, {}))


@pytest.mark.parametrize("tool", ["mcp__zotero__zotero_delete_item", "mcp__claude_ai_Gmail__send_message", "mcp__zotero__zotero_search_items2", "mcp__other__x"])
def test_other_mcp_tools_denied(run_hook, proj, tool):
    denied(call(run_hook, proj, tool, {}))


# --- malformed input
@pytest.mark.parametrize("raw", ["", "not json", "[]", '{"tool_name": 5}', '{"tool_name": "Bash", "tool_input": []}'])
def test_malformed_input_while_active_denies(proj, raw):
    rc, out, err = call(None, proj, "", {}, raw=raw)
    assert rc == 2 and json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_malformed_input_while_inactive_is_silent(proj):
    rc, out, _ = call(None, proj, "", {}, active=None, raw="not json")
    assert rc == 0 and out == ""


# --- the older write guard must not mask a deny
def test_safety_guard_defers_to_the_unattended_guard(run_hook, proj):
    r = run_hook(SAFETY, {"tool_name": "Write", "tool_input": {"file_path": str(proj / "package.json"), "content": "x"}},
                 {"CLAUDE_PROJECT_DIR": str(proj), "WREN_UNATTENDED": "1"})
    assert r.returncode == 2 and r.json["hookSpecificOutput"]["permissionDecision"] == "deny"
    ok = run_hook(SAFETY, {"tool_name": "Write", "tool_input": {"file_path": str(proj / "outputs" / "librarian" / f"report_{D}.md"), "content": "x"}},
                  {"CLAUDE_PROJECT_DIR": str(proj), "WREN_UNATTENDED": "1"})
    assert ok.returncode == 0 and "approve" not in ok.stdout


def test_safety_guard_unchanged_when_interactive(run_hook, proj):
    r = run_hook(SAFETY, {"tool_name": "Write", "tool_input": {"file_path": str(proj / "package.json"), "content": "x"}}, {"CLAUDE_PROJECT_DIR": str(proj)})
    assert r.returncode == 0 and r.json == {"decision": "approve"}


# --- registration
def test_settings_register_the_guard_on_all_three_matchers():
    s = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text())
    by = {e["matcher"]: [h["command"] for h in e["hooks"]] for e in s["hooks"]["PreToolUse"]}
    guard = "pre-tool-unattended-guard.sh"
    assert any(guard in c for c in by["Bash"])
    assert any(guard in c for c in by["mcp__.*"])
    write = by["Write|Edit|MultiEdit|NotebookEdit"]
    assert guard in write[0] and "pre-write-safety-guard.sh" in write[1]
