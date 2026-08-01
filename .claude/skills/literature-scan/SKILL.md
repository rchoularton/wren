---
name: literature-scan
description: Search recent publications on a topic - flag scooping risks, find citation gaps
user-invocable: true
argument-hint: [topic-or-paper-id]
---

# Literature Scan

## Purpose

Search for recent publications relevant to a topic or a paper. Used in Phase 1 (exploration — what exists?) and Phase 8 (pre-writing — anything new since the analysis was frozen?). Identifies scooping risks and citation gaps.

The scan's field and vocabulary are **never hardcoded** — they come from `research-config.yml` (`project.discipline`, `domain.key_terms`) and, when a paper id is given, from that paper's `STATUS.md` / `config.json`. This keeps the skill discipline-agnostic.

## Usage

```bash
/literature-scan example-paper                       # Full scan for a paper's topic
/literature-scan example-paper --scooping            # Focus on scooping risk
/literature-scan example-paper --gaps                # Find citation gaps in the draft
/literature-scan --topic "your specific topic here"  # Ad-hoc scan, no paper needed
```

The argument is either a paper id (a folder under `papers/`) or a free-text `--topic`. Flags `--scooping`, `--gaps`, and `--topic` narrow the scan; with none, run the full workflow.

## Workflow

### Step 1: Establish the topic

**If a paper id was given:**
1. Read `papers/{id}/STATUS.md` for the research focus.
2. Read `papers/{id}/PLAN.md` for the argument structure.
3. Read `papers/{id}/config.json` for the target journal.
4. If a draft exists in `papers/{id}/drafts/`, read it for existing citations.
5. Extract key terms, methods, and findings.

**If only `--topic` was given (or to enrich a paper scan):**
1. Read `research-config.yml` → `project.discipline` for the field.
2. Read `research-config.yml` → `domain.key_terms` for the vocabulary to treat as first-class search terms.
3. Read `research-config.yml` → `journals.default` / `journals.targets` for the venues to watch.

If `domain.key_terms` is empty and no paper id was given, ask the user for two or three terms before searching — do not guess the field.

### Step 2: Build the search strategy

Construct search queries by combining:
- The paper title and abstract keywords (if a paper id was given).
- The discipline description from `project.discipline`.
- The vocabulary from `domain.key_terms`.
- Methodology terms extracted from `PLAN.md` / the draft.
- Any geographic or population scope stated in the paper.
- Competing author names, if known.

### Step 3: Search

Use **WebSearch** as the primary discovery tool. Query for:
1. **Recent peer-reviewed papers** — last 12 months, matching the paper's question.
2. **Target-journal issues** — recent contents of the journals in `journals.targets`.
3. **Preprint / working-paper servers** appropriate to the discipline (e.g. arXiv, SSRN, bioRxiv, RePEc — pick the ones that fit `project.discipline`).
4. **Field organisations and agencies** — the bodies that publish in the user's discipline. Derive these from `project.discipline` and `domain.key_terms`; do not assume any fixed set of organisations.

Look for:
- Direct competitors (same research question).
- Methodological precedents (same approach, possibly a different subject area).
- Recent datasets, or updates to the data the paper uses.
- Reports or reviews that cite similar findings.

### Step 4: Check the reference library

Cross-reference each finding against the user's own references, using whichever provider `research-config.yml` → `references.provider` names:

- **`bibtex` (default):** read `references.bibtex_path` (default `references/library.bib`) and match found publications by title / DOI / author-year. This needs no external service.
- **`zotero` (optional):** if configured, use the Zotero MCP tools (`zotero_search_items`, `zotero_item_metadata`) for a live-library check with full-text and PDFs. Only use these when the provider is `zotero` — never hard-require them.

From the cross-reference:
1. Identify publications that should be cited but are not in the draft.
2. Flag library entries that look outdated (superseded by newer work found in Step 3).

### Step 5: Scooping assessment (if `--scooping` or full scan)

For each potentially competing publication, judge overlap against the paper's question **and** against the user's other papers in `papers/` — a neighbouring paper of theirs can be the thing at risk, not just outside work.

| Publication | Overlap | Scooping Risk | Our Differentiation |
|-------------|---------|---------------|---------------------|
| Author et al. 2025, Journal A | Methods overlap | Medium | Different data source, longer time period |
| Author et al. 2026, Journal B | Findings overlap | High | Need to cite and differentiate |

**Risk levels:**
- **High** — same question, similar method, similar findings → must cite and clearly differentiate.
- **Medium** — overlapping topic, different angle → cite and position.
- **Low** — related work that strengthens context → cite in the introduction.

### Step 6: Citation gap analysis (if `--gaps` or full scan)

Compare the draft's citations against:
- Foundational methodological papers (the methods used should be attributed).
- Recent papers on the same topic (cite, or explain the omission).
- Documentation for every dataset the paper uses.
- Journal norms — what do comparable papers in the target journal cite?

### Step 7: Report

```markdown
# Literature Scan — {topic or paper id}
**Date:** YYYY-MM-DD
**Scope:** [Full / Scooping / Gaps / Topic-specific]

## Scooping Risk Assessment
| Risk Level | Count |
|------------|-------|
| High   | 0 |
| Medium | 2 |
| Low    | 5 |

## Key Publications Found
1. **[Title]** — [Authors, Journal, Year]
   - Relevance: [description]
   - In reference library: Yes/No
   - Cited in draft: Yes/No
   - Action: [Cite / Read / Monitor]

## Citation Gaps
- [Papers that should be cited but aren't]

## Recommendations
- [Prioritised list of actions]
```

### Step 8: Save

1. Save the report to `papers/{id}/literature/literature_scan_YYYY-MM-DD.md` (create the folder if needed). For an ad-hoc `--topic` scan with no paper, ask the user where to save it.
2. Ask: "Should I add any of these to your reference library?" (append to `references/library.bib`, or add to Zotero if that provider is configured).
3. Update `papers/{id}/STATUS.md` if the scan affects phase readiness.

## When done

Ask about saving findings to `papers/{id}/NOTES.md`.
