"""Tests for the post-agent-review-gate PostToolUse hook."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest
from conftest import REPO_ROOT

HOOK = REPO_ROOT / ".claude" / "hooks" / "post-agent-review-gate.py"

EDITOR_FILES = [
    "journal_guidelines.md",
    "reviewer_methods_v{N}.md",
    "reviewer_significance_v{N}.md",
    "reviewer_presentation_v{N}.md",
]
COMPARATIVE = "comparative_analysis_v{N}.md"
QC_FILES = ["skeptic_review_v{N}.md", "responder_review_v{N}.md"]


def _populate(root, names, n):
    reviews = root / "papers" / "example-paper" / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    for name in names:
        (reviews / name.format(N=n)).write_text("x\n")


def _brief(n, names):
    refs = " ".join(f"papers/example-paper/reviews/{x.format(N=n)}" for x in names)
    return f"Write the verdict for example-paper. Inputs: {refs}"


def _event(subagent, prompt, tool="Agent"):
    return {"tool_name": tool, "tool_input": {"subagent_type": subagent, "prompt": prompt}}


def _run(run_hook, root, event):
    return run_hook(HOOK, event, {"CLAUDE_PROJECT_DIR": str(root)})


def _assert_silent(res):
    assert res.returncode == 0
    assert res.stdout == ""
    assert res.stderr == ""


@pytest.mark.parametrize("tool", ["Agent", "Task"])
def test_editor_all_present_is_silent(run_hook, scaffold_project, tool):
    _populate(scaffold_project, EDITOR_FILES + [COMPARATIVE], 2)
    ev = _event("peer-review-editor", _brief(2, EDITOR_FILES[1:] + [COMPARATIVE]), tool)
    _assert_silent(_run(run_hook, scaffold_project, ev))


def test_editor_missing_required_blocks(run_hook, scaffold_project):
    names = [f for f in EDITOR_FILES if "presentation" not in f] + [COMPARATIVE]
    _populate(scaffold_project, names, 2)
    ev = _event("peer-review-editor", _brief(2, EDITOR_FILES[1:]))
    res = _run(run_hook, scaffold_project, ev)
    assert res.returncode == 0
    assert set(res.json) == {"decision", "reason"}
    assert set(res.json) == {"decision", "reason"}
    assert res.json["decision"] == "block"
    assert "reviewer_presentation_v2.md" in res.json["reason"]
    assert "example-paper" in res.json["reason"]
    assert "reviewer_methods_v2.md" not in res.json["reason"]


def test_editor_missing_comparative_warns(run_hook, scaffold_project):
    _populate(scaffold_project, EDITOR_FILES, 2)
    ev = _event("peer-review-editor", _brief(2, EDITOR_FILES[1:]))
    res = _run(run_hook, scaffold_project, ev)
    assert res.returncode == 0
    assert set(res.json) == {"hookSpecificOutput"}
    out = res.json["hookSpecificOutput"]
    assert set(out) == {"hookEventName", "additionalContext"}
    assert out["hookEventName"] == "PostToolUse"
    assert "comparative" in out["additionalContext"]


def test_team_leader_missing_responder_blocks(run_hook, scaffold_project):
    _populate(scaffold_project, ["skeptic_review_v1.md"], 1)
    ev = _event("qc-team-leader", _brief(1, QC_FILES))
    res = _run(run_hook, scaffold_project, ev)
    assert res.returncode == 0
    assert set(res.json) == {"decision", "reason"}
    assert res.json["decision"] == "block"
    assert "responder_review_v1.md" in res.json["reason"]
    assert "skeptic_review_v1.md" not in res.json["reason"]


def test_team_leader_all_present_is_silent(run_hook, scaffold_project):
    _populate(scaffold_project, QC_FILES, 1)
    ev = _event("qc-team-leader", _brief(1, QC_FILES))
    _assert_silent(_run(run_hook, scaffold_project, ev))


def test_two_versions_fails_open(run_hook, scaffold_project):
    # Nothing on disk: a pinned run would block, so silence proves fail-open.
    prompt = (
        "papers/example-paper/reviews/skeptic_review_v1.md and "
        "papers/example-paper/reviews/responder_review_v2.md"
    )
    _assert_silent(_run(run_hook, scaffold_project, _event("qc-team-leader", prompt)))


def test_other_subagent_is_silent(run_hook, scaffold_project):
    ev = _event("Explore", _brief(1, QC_FILES))
    _assert_silent(_run(run_hook, scaffold_project, ev))


def test_malformed_and_wrong_types_are_silent(run_hook, scaffold_project):
    env = {"CLAUDE_PROJECT_DIR": str(scaffold_project)}
    proc = subprocess.run(
        [sys.executable, str(HOOK)], input="{not json", capture_output=True,
        text=True, env=env, timeout=30,
    )
    assert proc.returncode == 0 and proc.stdout == ""

    listy = _event(["qc-team-leader"], _brief(1, QC_FILES))
    _assert_silent(_run(run_hook, scaffold_project, listy))
    nonstr_prompt = _event("qc-team-leader", ["papers/example-paper/reviews/x_v1.md"])
    _assert_silent(_run(run_hook, scaffold_project, nonstr_prompt))


def test_version_from_prose_fallback(run_hook, scaffold_project):
    prompt = "Synthesise version 3 for papers/example-paper/drafts/x.md"
    _populate(scaffold_project, QC_FILES, 3)
    _assert_silent(_run(run_hook, scaffold_project, _event("qc-team-leader", prompt)))

    (scaffold_project / "papers/example-paper/reviews/responder_review_v3.md").unlink()
    res = _run(run_hook, scaffold_project, _event("qc-team-leader", prompt))
    assert res.returncode == 0
    assert set(res.json) == {"decision", "reason"}
    assert res.json["decision"] == "block"
    assert "responder_review_v3.md" in res.json["reason"]


def test_draft_version_does_not_pin(run_hook, scaffold_project):
    _populate(scaffold_project, QC_FILES, 1)
    prompt = _brief(1, QC_FILES) + " Draft: papers/example-paper/drafts/v3.md (draft v3)."
    _assert_silent(_run(run_hook, scaffold_project, _event("qc-team-leader", prompt)))


def test_dotted_version_fails_open(run_hook, scaffold_project):
    prompt = "Synthesise version 2.1 of papers/example-paper/drafts/x.md"
    _assert_silent(_run(run_hook, scaffold_project, _event("qc-team-leader", prompt)))


def test_prior_round_citation_is_ignored(run_hook, scaffold_project):
    _populate(scaffold_project, ["skeptic_review_v2.md"], 2)
    prompt = (
        "Inputs: papers/example-paper/reviews/skeptic_review_v2.md "
        "papers/example-paper/reviews/responder_review_v2.md "
        "(prior: papers/example-paper/reviews/team_leader_synthesis_v1.md)"
    )
    res = _run(run_hook, scaffold_project, _event("qc-team-leader", prompt))
    assert res.returncode == 0
    assert set(res.json) == {"decision", "reason"}
    assert res.json["decision"] == "block"
    assert "responder_review_v2.md" in res.json["reason"]


def test_block_mentions_missing_comparative(run_hook, scaffold_project):
    _populate(scaffold_project, [f for f in EDITOR_FILES if "presentation" not in f], 2)
    ev = _event("peer-review-editor", _brief(2, EDITOR_FILES[1:]))
    res = _run(run_hook, scaffold_project, ev)
    assert set(res.json) == {"decision", "reason"}
    assert res.json["decision"] == "block"
    assert "comparative_analysis" in res.json["reason"]


def test_multi_digit_dotted_version_fails_open(run_hook, scaffold_project):
    _populate(scaffold_project, QC_FILES, 1)
    prompt = "papers/example-paper/ version 12.1"
    _assert_silent(_run(run_hook, scaffold_project, _event("qc-team-leader", prompt)))


OUTPUT_BRIEF = (
    "Draft is version 3 of the manuscript; write papers/example-paper/reviews/peer_review_v1.md"
)


def test_output_filename_outranks_prose_version(run_hook, scaffold_project):
    _populate(scaffold_project, EDITOR_FILES + [COMPARATIVE], 1)
    ev = _event("peer-review-editor", OUTPUT_BRIEF)
    _assert_silent(_run(run_hook, scaffold_project, ev))

    (scaffold_project / "papers/example-paper/reviews/reviewer_presentation_v1.md").unlink()
    res = _run(run_hook, scaffold_project, ev)
    assert res.returncode == 0
    assert set(res.json) == {"decision", "reason"}
    assert res.json["decision"] == "block"
    assert "reviewer_presentation_v1.md" in res.json["reason"]


def test_output_filename_with_draft_path_pins_v2(run_hook, scaffold_project):
    prompt = (
        "write papers/example-paper/reviews/peer_review_v2.md for "
        "papers/example-paper/drafts/v3.md"
    )
    res = _run(run_hook, scaffold_project, _event("peer-review-editor", prompt))
    assert set(res.json) == {"decision", "reason"}
    assert res.json["decision"] == "block"
    assert "v2" in res.json["reason"]


def test_sentence_final_period_still_pins(run_hook, scaffold_project):
    ev = _event("qc-team-leader", "Synthesise papers/example-paper/ version 2.")
    res = _run(run_hook, scaffold_project, ev)
    assert res.returncode == 0
    assert set(res.json) == {"decision", "reason"}
    assert res.json["decision"] == "block"
    assert "v2" in res.json["reason"]

    dotted = _event("qc-team-leader", "Synthesise papers/example-paper/ version 2.1")
    _assert_silent(_run(run_hook, scaffold_project, dotted))
