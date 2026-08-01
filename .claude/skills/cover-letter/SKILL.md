---
name: cover-letter
description: Draft a journal-specific cover letter from a paper's frozen findings
user-invocable: true
argument-hint: [paper-id]
---

# Cover Letter

Draft a journal-specific cover letter that highlights the paper's contribution and fit. Phase 13 of the 14-phase pipeline. Draws from the frozen gold-standard outputs and the final manuscript.

## Usage

```bash
/cover-letter example-paper       # Use the journal from the paper's config
```

The target journal comes from the paper's `config.json` (`journal` field), falling back to `research-config.yml` (`journals.default`). The field/discipline comes from `research-config.yml` (`project.discipline`).

## Before drafting

1. Confirm the paper's phase in `papers/{id}/STATUS.md` is far enough along that the analysis is frozen (Phase 7, `/gold-standard`) and the manuscript is drafted. If not, say so and stop.
2. Read `papers/{id}/config.json` for the journal, title, and author info.
3. Read the current manuscript in `papers/{id}/drafts/` for the abstract, key findings, and conclusions.
4. Read `papers/{id}/STATUS.md` for the key-findings summary and the contribution statement.
5. Pull the frozen numbers from `papers/{id}/gold_standard/`.
6. Fetch the journal's aims and scope with WebSearch / WebFetch (provider-agnostic).

## Workflow

### Step 1: Identify the key selling points

Extract from the paper:

1. **Novelty** — what is new? First study to...?
2. **Significance** — why does this matter? What are the implications?
3. **Timeliness** — why now? Recent data, current developments?
4. **Methodological contribution** — a new approach?
5. **Data contribution** — a unique dataset?
6. **Journal fit** — why this journal specifically?

### Step 2: Draft the cover letter

Follow a standard academic cover-letter structure:

```markdown
[Date]

Dear [Editor name / "Editors of {Journal}"],

**Re: Submission of "[Paper Title]"**

We are pleased to submit our manuscript entitled "[Title]" for
consideration as a [Article type] in [Journal].

[Para 1: What the paper does — research question and approach]

[Para 2: Key findings — 2-3 headline results with numbers]

[Para 3: Significance — why this matters for the field]

[Para 4: Journal fit — why this journal is the right venue]

[Para 5: Declarations — no conflicts, not under review elsewhere,
all authors approved, word count, number of display items]

We look forward to your consideration.

Sincerely,
[Corresponding author]
[Affiliation]
[ORCID]
```

Pull the author name, affiliation, and ORCID from `config.json` / `research-config.yml`. Do not invent them.

### Step 3: Output

1. Save the markdown to `papers/{id}/reviews/cover_letter.md` (or `papers/{id}/cover_letter.md` if the paper has no `reviews/` directory).
2. Present the draft one section at a time and ask for revisions (`.claude/rules/one-at-a-time.md`).
3. Update `papers/{id}/STATUS.md`.

## Drafting rules

- **Keep to one page** (300-400 words).
- **Lead with the finding**, not the methodology.
- **Every number** comes from the frozen gold-standard outputs — quote the source, never estimate.
- **Match the journal's tone** — broad-significance journals want the wider implication up front; specialist journals want relevance to their community. Read the aims and scope you fetched and mirror them.
- **Name the editor** if the journal lists a handling editor for the section.
- **Never claim "novel" unless it truly is** — prefer "first systematic", "comprehensive", or a precise description of what the study adds.
- **Human prose, not AI-tells:** no em-dashes, no formulaic connectives, varied sentence rhythm (see `.claude/rules/reviewer-response-prose.md`).
- Do not add scope or extra deliverables the user has not approved (`.claude/rules/no-unapproved-tasks.md`).

## When done

Ask whether the user wants the letter built to Word alongside the manuscript.
