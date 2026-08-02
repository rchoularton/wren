---
name: ref-check
description: Validate a draft's citations against your reference library, find uncited claims, and check journal formatting
user-invocable: true
argument-hint: "<paper-id> [--format] [--gaps] [--zotero]"
---

# Reference Check

Validate every citation in a paper draft against your reference library, find claims that
lack a citation, and check formatting against the target journal. A natural pre-submission
pass (Phase 10 of the pipeline).

Works with either reference provider: on `zotero`, use the live library via the Zotero MCP; on
`bibtex`, check against the `.bib` file at `references.bibtex_path`.

## Usage

```
/ref-check my-paper            # full check
/ref-check my-paper --format   # formatting only
/ref-check my-paper --gaps     # find uncited claims only
/ref-check my-paper --zotero   # verify every ref exists in the library
```

## What to do

1. **Gather.** Read the current draft (from `papers/{id}/drafts/`, or the `onedrive_path` in
   `config.json`) and the target `journal` from `config.json`. Extract the in-text citations
   and the reference list.

2. **Inventory.** Build a table: in-text citation → is it in the reference list? → is it in
   your library? → is the format correct? Flag any row that fails a column.

3. **Verify against the library** (full check or `--zotero`). For each citation:
   - **Find it** — search the library (Zotero MCP search tools, or the `.bib`). Retry with
     broader terms if the first search misses.
   - **Check metadata** — title, authors, year, journal/publisher, DOI, pages. Flag missing
     DOIs and any mismatch between the in-text year/author and the actual record.
   - **Check support** (Zotero, where full text is available) — read the source and confirm it
     actually supports the specific claim; note the passage. Especially for statistics,
     methods, and headline findings.

4. **Gap analysis** (full check or `--gaps`). Scan the draft for factual/statistical claims,
   methodological claims, and vague "previous studies show…" statements that lack a citation.
   For each, search the library for a candidate and quote the supporting passage; if none is
   found, flag it for the user to research.

5. **Format check** (full check or `--format`). Compare the citation style to the journal's
   requirements: in-text style (numbered vs author-year, et al. threshold), reference-list
   format (journal abbreviations, DOI inclusion, page numbers), ordering, and any data/code
   availability statements.

6. **Report** — a summary table (total citations, in reference list, in library, correctly
   formatted, uncited claims found) then the detailed issues, items missing from the library
   (with suggested search terms), and format corrections (before → after). Offer to save to
   `papers/{id}/reviews/ref_check_v{N}.md`.

## After the check

- Offer to fix formatting issues in the draft (propose each change, wait for approval).
- **Missing references:** present them as a batch (citation, type, DOI/URL) and offer to add
  the approved ones to your library — via the Zotero MCP if it supports writes, or by giving
  the user the details to add. Re-check each afterward.
- **If `integrations.gmail` is enabled and the paper has co-authors**, offer to draft (never
  send) a Gmail to them summarizing the findings, with the report path. Get addresses from
  `config.json` if stored, otherwise ask.
- Note whether the paper is clear for the next phase, and ask about recording findings in
  `NOTES.md`.
