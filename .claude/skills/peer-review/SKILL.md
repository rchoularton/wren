---
name: peer-review
description: Agentic peer review — three independent referee sub-agents (methods, significance, presentation) plus a handling editor evaluate a paper against its target journal's guidelines and issue a decision with a prioritized action list
user-invocable: true
argument-hint: [paper-id] [--journal "Journal Name"] [--skip-examples] [--section "name"]
---

# Peer Review

Simulates a journal's referee process. Three **independent reviewer sub-agents** read the
draft in isolation (`.claude/agents/peer-reviewer-methods.md`, `peer-reviewer-significance.md`,
`peer-reviewer-presentation.md`), then a **handling editor** (`peer-review-editor.md`)
reconciles their reports into one decision. The reviewers run isolated for the same reason a
real journal uses independent referees — one reviewer must not be primed by another's reasoning.

The orchestrator (this skill) runs the two research stages that need the web (journal
guidelines, comparable papers), fans out to the reviewers, then hands the editor the finished
reports. It runs on the main loop, so the checkpoints below are real pauses — stop and wait.

A natural fit for **Phase 10 (internal review)** of the pipeline; run it after the analysis is
frozen (`/gold-standard`, Phase 7) and a full draft exists.

## Usage

```
/peer-review my-paper --journal "Journal of Example Studies"
/peer-review my-paper --journal "Journal of Example Studies" --skip-examples
/peer-review my-paper --journal "Journal of Example Studies" --section "discussion"
```

## Parameters

- `paper-id` (required): Paper identifier (e.g. `my-paper`). Maps to `papers/{id}/`.
- `--journal "Name"`: Target journal. If omitted, resolve it (see below).
- `--skip-examples`: Skip Stage 2 (comparative analysis) for a faster review.
- `--section "name"`: Focus the reviewers on a single section.

## Argument parsing

- `paper-id`: first argument after the command. If absent, ask which paper to review.
- `--journal "Name"`: target journal. Resolve in this order: the `--journal` flag →
  `papers/{id}/config.json` → `journal` → `research-config.yml` → `journals.default`. If none
  yields a journal, ask which to target.
- `--skip-examples`, `--section "name"`: as above.

## Workflow (orchestration)

### Step 0 — Gather context
Read, in order: `papers/{id}/STATUS.md`; the latest draft (most recent Markdown under
`papers/{id}/drafts/`); the outputs the paper cites (CSV/JSON in `outputs/` or
`papers/{id}/outputs/`); and any prior reviews under `papers/{id}/reviews/`. Compute the next
version number `N` (highest existing `peer_review_v{N}.md` + 1). If there is no draft, stop and
say so.

### Stage 1 — Guidelines ingestion
1. Check for cached guidelines at `papers/{id}/reviews/journal_guidelines.md`; reuse if present
   and current.
2. Otherwise `WebSearch` "[journal] submission guidelines author guidelines", `WebFetch` the
   page, and extract: word limits (abstract, main text), display-item limits (figures, tables),
   reference requirements, review dimensions, and scope/fit. Save as a structured checklist to
   `papers/{id}/reviews/journal_guidelines.md`.
3. **CHECKPOINT** — show the extracted criteria and confirm they look right before continuing.
   If cached guidelines conflict with a fresh fetch, prefer the fetch and note the difference.

### Stage 2 — Comparative analysis (skip if `--skip-examples`)
1. `WebSearch` for recent papers in this journal on related topics.
2. Find 3-5 comparable papers; for each note structure, novelty framing, citation patterns, and
   how implications are pitched. If fewer than 3 exist, say so and proceed.
3. Save a "success pattern" summary to `papers/{id}/reviews/comparative_analysis_v{N}.md`.
4. **CHECKPOINT** — confirm the example set is representative before the reviewers use it.

### Stage 3 — Three independent referee reports
Invoke the three reviewer sub-agents via the Agent tool. They can run **in parallel** (send the
three Agent calls in one message) — they are independent and must not see each other. Give each
a self-contained brief: the paper id, the absolute draft path, the guidelines path, the version
`N`, the prior-review paths, and (where relevant) the absolute paths of the cited data files and
the comparative-analysis file. Pass `--section` through if set. Each saves its own report:

| Sub-agent | Lens | Scores | Saves to |
|-----------|------|--------|----------|
| `peer-reviewer-methods` | methods, data, stats, reproducibility | Methodology | `reviewer_methods_v{N}.md` |
| `peer-reviewer-significance` | originality, contribution, literature, fit | Originality, Significance, Journal Fit | `reviewer_significance_v{N}.md` |
| `peer-reviewer-presentation` | writing, structure, figures, format limits | Presentation | `reviewer_presentation_v{N}.md` |

Wait for all three; confirm the three files exist before continuing.

### Stage 4 — Editorial decision
Invoke `peer-review-editor` with: the paper id, draft path, guidelines path, the three referee
report paths, the cited data-file paths (it spot-checks the highest-stakes disputes itself), and
version `N`. It computes the weighted overall, issues the decision, and writes two files:
`peer_review_v{N}.md` (the decision) and `recommendations_v{N}.md` (the prioritized action list).
Wait for completion; confirm both files exist.

### Step 5 — Present
Read the editor's `peer_review_v{N}.md` and show the user: the score table, the overall score
and decision, and the editorial summary. Then present the **Must-Fix** items from
`recommendations_v{N}.md`. Present findings and any decisions **one at a time**
(`.claude/rules/one-at-a-time.md`) — do not dump the whole action list in one message. Offer to
update `papers/{id}/STATUS.md` with the score and decision, and to note the review in the paper's
notes. Do not add scope beyond the review itself (`.claude/rules/no-unapproved-tasks.md`).

## Output files

```
papers/{id}/reviews/
  journal_guidelines.md              ← Stage 1 (cached, not versioned)
  comparative_analysis_v{N}.md       ← Stage 2 (unless --skip-examples)
  reviewer_methods_v{N}.md           ← peer-reviewer-methods
  reviewer_significance_v{N}.md      ← peer-reviewer-significance
  reviewer_presentation_v{N}.md      ← peer-reviewer-presentation
  peer_review_v{N}.md                ← peer-review-editor (decision)
  recommendations_v{N}.md            ← peer-review-editor (action list)
```

## Scoring framework

The editor computes one weighted overall from the referees' dimension scores:

| Dimension | Weight | Referee |
|-----------|--------|---------|
| Originality | 20% | significance |
| Methodology | 25% | methods |
| Significance | 20% | significance |
| Presentation | 15% | presentation |
| Journal Fit | 20% | significance |

Decision bands: **85-100** accept with minor revisions · **70-84** major revisions ·
**50-69** reject and resubmit · **< 50** reject.

## Why four sub-agents, not one loop
- **Independence** — three referees who cannot see each other's reasoning give a cleaner signal
  than one context scoring five dimensions in sequence, exactly as a journal uses independent
  reviewers.
- **Tool budget per referee** — each reviewer gets its own budget to verify claims against the
  data or search the literature; one shared context exhausts it.
- **Honest adjudication** — the editor reads three finished reports as artifacts and reconciles
  them, rather than a single voice grading its own work.
- **Reusability** — another skill can invoke `peer-reviewer-methods` directly without the
  orchestrator.

## Notes
- This skill critiques an existing draft. To produce the revisions, hand `recommendations_v{N}.md`
  to `/draft`; the analysis behind the paper should already be frozen via `/gold-standard`.
- Reviewers verify against the source data and the journal guidelines — they do not trust the
  draft's own numbers (`.claude/rules/rigor.md`, no fabrication or embellishment).
- The `peer-reviewer-presentation` agent runs on the `sonnet` tier and the other three on `opus`
  (see the token-budget rule). Bump presentation to `opus` in its agent file if you want the
  full critique tier on every referee.
