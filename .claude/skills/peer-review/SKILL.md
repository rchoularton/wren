---
name: peer-review
description: Agentic peer reviewer that evaluates a paper against its target journal's guidelines in four stages
user-invocable: true
argument-hint: [paper-id] [--journal "Journal Name"] [--skip-examples] [--section "name"]
context: fork
---

# Peer Review

Multi-stage peer review agent that:
1. Ingests the target journal's review guidelines
2. Analyzes recent similar publications
3. Conducts a section-by-section review
4. Generates actionable recommendations

Run every stage. This skill runs in a forked context, so the interactive checkpoints below cannot pause for a live reply — treat each checkpoint as a written self-check: state the decision you would ask for, resolve it explicitly, and record it in the output. Never silently drop a stage (`.claude/rules/rigor.md`).

## Usage

```bash
/peer-review example-paper --journal "Journal of Example Studies"
/peer-review example-paper --journal "Journal of Example Studies" --skip-examples
/peer-review example-paper --journal "Journal of Example Studies" --section "discussion"
```

## Parameters

- `paper-id` (required): Paper identifier (e.g., "example-paper"). Maps to `papers/{id}/`.
- `--journal "Name"`: Target journal name. If omitted, resolve it (see below).
- `--skip-examples`: Skip Stage 2 (comparative analysis) for a faster review.
- `--section "name"`: Review only a specific section.

## Argument Parsing

Parse the user's command for:
- `paper-id`: First argument after the command.
- `--journal "Name"`: Target journal.
- `--skip-examples`: Skip comparative analysis.
- `--section "name"`: Review a specific section only.

If no `paper-id` is provided, ask which paper to review.

Resolve the target journal in this order:
1. The `--journal` flag, if given.
2. `papers/{id}/config.json` → `journal`.
3. `research-config.yml` → `journals.default`.

If none of these yields a journal, ask which journal to target.

## Workflow

The agent runs through 4 stages, each with a checkpoint.

### Stage 1: Guidelines Ingestion

1. Search for "[journal name] submission guidelines author guidelines" using WebSearch.
2. Fetch the guidelines page using WebFetch.
3. Extract key criteria:
   - Word limits (abstract, main text)
   - Display item limits (figures, tables)
   - Reference requirements
   - Review dimensions (originality, methodology, significance)
   - Scope/fit requirements
4. Format as a structured checklist.
5. Check for existing cached guidelines in `papers/{id}/reviews/journal_guidelines.md`; reuse if present and current, otherwise refetch.
6. **CHECKPOINT**: Confirm the criteria look correct before continuing. If cached guidelines conflict with the fetched page, prefer the fresh fetch and note the difference.

### Stage 2: Comparative Analysis (skip if --skip-examples)

1. Search for recent papers in this journal on related topics using WebSearch.
2. Find 3-5 comparable papers (similar methodology, topic area).
3. For each paper, analyze: structure, novelty framing, citation patterns, implications style.
4. Generate a "success pattern" summary.
5. **CHECKPOINT**: Confirm the example set is representative before analyzing it. If fewer than 3 comparable papers are found, say so and proceed with what is available.

### Stage 3: Section-by-Section Review

1. Find the latest draft — the most recent Markdown file in `papers/{id}/drafts/`.
2. Read the full draft.
3. For each section (Abstract, Introduction, Results, Discussion, Methods):
   - Count words
   - Check against limits
   - Score against journal criteria (0-100)
   - Generate specific feedback
   - Note questions a reviewer might ask
4. Analyze figures/tables: count, check against limits, assess quality against the draft's own description of each.
5. **CHECKPOINT**: Confirm section scores before moving to the final report.

Only state what the draft and its underlying outputs actually contain. Do not describe a figure, value, or claim you have not verified in the source (`.claude/rules/rigor.md`).

### Stage 4: Report Generation

1. Calculate the overall score using a weighted framework:
   - Originality (20%)
   - Methodology (25%)
   - Significance (20%)
   - Presentation (15%)
   - Journal Fit (20%)

2. Determine the recommendation:
   - 85-100: Accept with minor revisions
   - 70-84: Major revisions
   - 50-69: Reject and resubmit
   - <50: Reject

3. Generate `peer_review_v{n}.md` with scores, section feedback, priority recommendations, reviewer questions, and journal fit analysis.

4. Generate `recommendations_v{n}.md` with prioritized action items (high/medium/low).

5. Save both files to `papers/{id}/reviews/`.

6. Offer to update `papers/{id}/STATUS.md` with the review score and record a summary in the paper's notes.

## Review Framework Details

**Originality (20%)** — Novel research question, advances beyond the literature, unique dataset or methodology.

**Methodology (25%)** — Data quality, analytical rigor, reproducibility, appropriate statistics.

**Significance (20%)** — Practical relevance, implications, field advancement, timeliness.

**Presentation (15%)** — Clear writing, logical structure, figure/table quality, appropriate length.

**Journal Fit (20%)** — Within scope, meets format requirements, appropriate audience, citation style.

## Notes

- Always read the draft BEFORE starting the review.
- Be specific with feedback — include line references where possible.
- Focus on actionable recommendations.
- Save all outputs to `papers/{id}/reviews/`.
- Present findings and any decisions one at a time (`.claude/rules/one-at-a-time.md`); do not add scope beyond the review itself (`.claude/rules/no-unapproved-tasks.md`).
- This skill critiques an existing draft. To produce revisions, hand results to `/draft`; the analysis behind the paper should already be frozen via `/gold-standard` (Phase 7 of the pipeline).
