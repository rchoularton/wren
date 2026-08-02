---
name: qc-team
description: Three-agent adversarial QC review (Skeptic / Responder / Team Leader) for a paper draft - verifies stats against source data, flags methodological and causal-language issues, and produces a Must-Fix / Should-Fix verdict
user-invocable: true
argument-hint: "<paper-id> [--skeptic-only]"
---

# QC Team Review

Adversarial three-agent QC for a paper draft. The personas run as **isolated sub-agents**
(`.claude/agents/qc-skeptic.md`, `qc-responder.md`, `qc-team-leader.md`), invoked via the
Agent tool. Context isolation matters: the Responder must not be primed by the Skeptic's
reasoning, and the Team Leader needs both reviews as finished artifacts, not interleaved chat.

A natural fit for Phase 6 (post-analysis QC) and Phase 11 (pre-submission QC) of the pipeline.

## Usage

```
/qc-team my-paper                 # full 3-agent review
/qc-team my-paper --skeptic-only  # just the Skeptic pass (faster)
```

## Workflow (orchestration)

### Step 0 — Gather context
Read, in order: `papers/{id}/STATUS.md`; the latest draft under `papers/{id}/drafts/`; the
outputs the paper cites (CSV/JSON in `outputs/` or `papers/{id}/outputs/`); and any prior
reviews under `papers/{id}/reviews/` (to catch regressions). Compute the next version number
`N` (highest existing `*_v{N}.md` + 1).

### Step 1 — Skeptic
Invoke the **`qc-skeptic`** sub-agent via the Agent tool with a self-contained brief: the
paper id, the absolute draft path, the absolute paths of the data files the paper cites (list
them explicitly), the version `N`, the prior-review paths, and the instruction to save to
`papers/{id}/reviews/skeptic_review_v{N}.md`. Wait for it to finish; confirm the file exists.

If `--skeptic-only`, skip to Step 4.

### Step 2 — Responder
Invoke **`qc-responder`** with: the paper id, draft path, the Skeptic's review path (Step 1),
the same data-file list, version `N`, and the instruction to save to
`papers/{id}/reviews/responder_review_v{N}.md`. It works in isolation so it sees only the
Skeptic's written review, not its reasoning. Wait; confirm the file exists.

### Step 3 — Team Leader
Invoke **`qc-team-leader`** with: the paper id, draft path, both review paths, the same
data-file list (it spot-checks Critical items itself), version `N`, and the instruction to
save to `papers/{id}/reviews/team_leader_synthesis_v{N}.md`. Wait for completion.

### Step 4 — Present
Read the Team Leader synthesis (or, with `--skeptic-only`, the Skeptic review) and show the
user: the summary table (Must-Fix / Should-Fix / Nice-to-Have), the overall verdict, and the
Must-Fix items with proposed fixes. Then ask: "Want me to implement the Must-Fix items?"
(For `--skeptic-only`: show the severity tally and top Critical items, and ask whether to run
the Responder + Team Leader.)

## Output files

```
papers/{id}/reviews/
  skeptic_review_v{N}.md          ← qc-skeptic
  responder_review_v{N}.md        ← qc-responder
  team_leader_synthesis_v{N}.md   ← qc-team-leader
```

## Why three sub-agents, not one loop
- **Context isolation** — the Responder seeing only the Skeptic's written review (not its
  reasoning trace) gives a cleaner adversarial signal.
- **Tool budget per persona** — each agent gets its own budget for verifying claims against
  the data; one shared context exhausts it.
- **Reusability** — other skills can invoke `qc-skeptic` directly without the orchestrator.

## Key principles
1. **Verify against data** — sub-agents spot-check the CSVs, they don't trust the draft.
2. **Be specific** — line numbers, exact statistics, file paths.
3. **Distinguish severity** — not everything is critical.
4. **Track regressions** — pass prior-review paths so the personas know what was already fixed.
5. **The Skeptic must be genuinely adversarial** — that's the only configuration where this
   skill earns its name.
