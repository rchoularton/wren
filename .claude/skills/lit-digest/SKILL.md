---
name: lit-digest
description: Lightweight weekly literature sweep across your papers - new publications in the last N days, aggregated into one digest with an optional Gmail draft
user-invocable: true
argument-hint: "[--since N] [--paper <id>]"
---

# Literature Digest

A fast, cross-paper scan for new work. One web search per paper, aggregated into a single
digest — lighter than `/literature-scan` (which goes deep on one topic). Designed to run
**headless on a schedule** (see the scheduled-jobs add-on) or on demand.

## Usage

```
/lit-digest                 # every active paper, last 7 days
/lit-digest --since 14      # last 14 days
/lit-digest --paper my-paper  # just one paper
```

## What to do

1. **Enumerate papers.** List `papers/*/` and read each `STATUS.md` (title, status) and
   `config.json` (journal). Skip any with `status: archived`. With `--paper`, do just that one.

2. **Build queries.** For each paper, derive 1–2 short search queries from its title,
   `STATUS.md`, and the project's `domain.key_terms` (from `research-config.yml`). Keep them
   specific — the paper's actual subject, not generic field terms.

3. **Search.** Run **one** `WebSearch` per paper, scoped to the window (`--since`, default 7
   days), taking the top ~5 results. (One search per paper keeps runtime and cost bounded —
   ~N papers × ~2 min.)

4. **Extract** each hit into a structured record: title, authors, venue, date, url, abstract
   (if available), and a one-line relevance note tying it to the paper. Collect everything
   into a single `items` list.

5. **Render two outputs from that same list** — they must contain the identical item set:
   - `outputs/lit_digests/digest_YYYY-MM-DD.md` — grouped by paper, human-readable.
   - `outputs/lit_digests/digest_YYYY-MM-DD.json` — the structured records.

   If the counts don't match, stop and rebuild — never ship a digest whose markdown and JSON
   disagree.

6. **Email (optional).** If `integrations.gmail.enabled: true`, create a **draft** (never
   send) with the markdown digest via your Gmail MCP's create-draft tool
   (`mcp__claude_ai_Gmail__create_draft` by default). If Gmail is disabled or unavailable, skip
   this step — the saved digest is the deliverable.

7. **Finish** with a one-line summary (papers scanned, new items found, output paths). A
   scheduled wrapper handles its own done/error notification.

## Rules

- **Headless-safe:** never block on a prompt — use the defaults above so a scheduled
  `claude -p "/lit-digest"` run completes unattended.
- **One search per paper.** Resist expanding to many searches; that's `/literature-scan`'s job.
- **Draft only, never send** email.
- Relevance notes must reflect the actual result, not be embellished (`.claude/rules/rigor.md`).

## Zotero ingest

This skill produces a digest; it does not add items to your library. Auto-ingesting the
DOI-verified hits into Zotero (with a review queue) arrives with `/librarian-team` — see the
[roadmap](https://rchoularton.github.io/wren/roadmap/).
