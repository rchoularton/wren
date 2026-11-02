#!/usr/bin/env python3
"""PostToolUse(Agent|Task) gate: a review verdict needs its prior stages on disk.

`/peer-review` and `/qc-team` end with a verdict sub-agent (`peer-review-editor`,
`qc-team-leader`). When one RETURNS, this hook checks that the earlier stage
files it depends on exist for the same paper and version, and BLOCKS with a
reason for the orchestrator if a required one is missing, so the verdict is not
accepted until the gap is filled (rigor rule 5, enforced structurally).

PostToolUse on the Agent call (not SubagentStop) because it fires in the main
session after the sub-agent returns, so a `decision: "block"` reason reaches the
orchestrator, the actor that accepts the verdict.

Guards:
  * Only acts on the two verdict sub-agent types; everything else exits 0.
  * Pins paper id and version N from the sub-agent's own brief
    (`tool_input.prompt`). If either is absent or ambiguous it fails open.
  * Missing comparative analysis (skippable via --skip-examples) only warns.
  * Never writes files; any error exits 0 with no output.

Contract: PostToolUse hooks get the tool call on stdin as JSON with `tool_name`
and `tool_input`; see https://code.claude.com/docs/en/hooks.md
"""
import json
import os
import re
import sys
from pathlib import Path

SUBAGENT_TOOLS = {"Task", "Agent"}

# verdict sub-agent -> required and warn-only files, each with the producing stage.
VERDICT_STAGES = {
    "peer-review-editor": {
        "required": {
            "journal_guidelines.md": "/peer-review Stage 1 (guidelines ingestion)",
            "reviewer_methods_v{N}.md": "/peer-review Stage 3 (peer-reviewer-methods)",
            "reviewer_significance_v{N}.md": "/peer-review Stage 3 (peer-reviewer-significance)",
            "reviewer_presentation_v{N}.md": "/peer-review Stage 3 (peer-reviewer-presentation)",
        },
        "warn": {
            "comparative_analysis_v{N}.md": "/peer-review Stage 2 (comparative analysis)",
        },
    },
    "qc-team-leader": {
        "required": {
            "skeptic_review_v{N}.md": "/qc-team Step 1 (qc-skeptic)",
            "responder_review_v{N}.md": "/qc-team Step 2 (qc-responder)",
        },
        "warn": {},
    },
}

SLUG = r"[A-Za-z0-9][A-Za-z0-9_-]*"


# Filename stems that are INPUTS to each verdict agent. Other review files a brief
# may cite (the verdict's own outputs, prior-round files) never pin the run.
INPUT_STEMS = {
    "peer-review-editor": {
        "reviewer_methods", "reviewer_significance", "reviewer_presentation",
        "comparative_analysis",
    },
    "qc-team-leader": {"skeptic_review", "responder_review"},
}


def pin_paper_and_version(prompt: str, subagent: str):
    """Return (paper_id, version) from the brief, or (None, None) if not unique.

    Prefers explicit `papers/<id>/reviews/<stem>_v<N>.md` references to this
    agent's input files; falls back to a lone `papers/<id>/` path plus a stated
    `version N` / `version number N` (a dotted version like 2.1 never pins).
    """
    stems = INPUT_STEMS[subagent]
    refs = [
        (p, stem, int(v))
        for p, stem, v in re.findall(
            rf"\bpapers/({SLUG})/reviews/([\w.-]*?)_v(\d+)\.md", prompt
        )
    ]
    # Priority: this agent's input files, then any other review file (its own
    # output names), then prose. Ambiguity at the chosen step fails open.
    chosen = [(p, v) for p, stem, v in refs if stem in stems] or [
        (p, v) for p, _, v in refs
    ]
    if chosen:
        papers = {p for p, _ in chosen}
        versions = {v for _, v in chosen}
    else:
        papers = set(re.findall(rf"\bpapers/({SLUG})/", prompt))
        versions = {
            int(v)
            for v in re.findall(r"\bversion\s+(?:number\s+)?(\d+)(?![\d.])", prompt, re.I)
        }
    if len(papers) != 1 or len(versions) != 1:
        return None, None
    return papers.pop(), versions.pop()


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(data, dict):
        return 0
    tool = data.get("tool_name")
    if isinstance(tool, str) and tool not in SUBAGENT_TOOLS:
        return 0

    ti = data.get("tool_input")
    if not isinstance(ti, dict):
        return 0
    subagent = ti.get("subagent_type")
    prompt = ti.get("prompt")
    if not isinstance(subagent, str) or not isinstance(prompt, str):
        return 0
    spec = VERDICT_STAGES.get(subagent)
    if spec is None:
        return 0

    paper, version = pin_paper_and_version(prompt, subagent)
    if paper is None or version is None:
        return 0

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
    reviews = root / "papers" / paper / "reviews"

    def absent(table):
        out = []
        for template, stage in table.items():
            name = template.format(N=version)
            if not (reviews / name).is_file():
                out.append((name, stage))
        return out

    missing = absent(spec["required"])
    warn = absent(spec["warn"])

    if missing:
        listing = "; ".join(f"{name} (produced by {stage})" for name, stage in missing)
        reason = (
            f"[review-gate] {subagent} returned a verdict for paper '{paper}' v{version}, "
            f"but required prior-stage files are missing from papers/{paper}/reviews/: "
            f"{listing}. Do not accept or present this verdict (rigor rule 5): run the "
            "missing stage(s), then re-run the verdict stage."
        )
        if warn:
            reason += (
                " Also absent: " + ", ".join(n for n, _ in warn)
                + " (skippable; confirm --skip-examples was intended)."
            )
        print(json.dumps({"decision": "block", "reason": reason}))
    elif warn:
        names = ", ".join(name for name, _ in warn)
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    f"[review-gate] {names} is absent for paper '{paper}' v{version}; "
                    "the comparative analysis was skipped, which is fine only if "
                    "--skip-examples was intended."
                ),
            }
        }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail open on anything unexpected
