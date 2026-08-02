---
name: zotero-audit
description: Scan your Zotero library for items missing metadata, tags, PDFs, or collections - produces an actionable cleanup queue
user-invocable: true
argument-hint: "[--collection <name>] [--since <YYYY-MM-DD>] [--fix]"
---

# Zotero Audit

Find Zotero items that need attention before you cite or scan them — missing metadata, no
tags/collections, no PDF — and produce a queue you can fix in bulk.

**Requires** `references.provider: zotero` in `research-config.yml` (the opt-in Zotero MCP).
On `bibtex`, there's no live library to audit — clean your source manager and re-export.

## Usage

```
/zotero-audit                          # audit the whole library
/zotero-audit --collection "Review"    # one collection
/zotero-audit --since 2026-01-01       # items added since a date
/zotero-audit --fix                    # propose metadata fixes, one at a time
```

## What to do

1. **Fetch items** via the Zotero MCP's search/metadata tools (filter by `--collection` or
   `--since` if given). Batch in chunks of ~50 to avoid timeouts.

2. **Check each item** and record what's missing:

   | Field | Why it matters |
   |---|---|
   | author / date / title | Missing any of these = can't be cited at all |
   | abstract | needed for topic matching and gap detection |
   | DOI | needed to cross-reference and auto-complete metadata |
   | journal / publisher | incomplete citation |
   | tags / collection | orphaned items drift and get lost |
   | PDF attachment | can't check full text or cite pages |

3. **Classify severity:**
   - 🔴 **Broken** — missing author OR date OR title. Cannot be cited.
   - ⚠️ **Incomplete** — missing abstract OR DOI OR journal. Citable but not verifiable.
   - ℹ️ **Unorganized** — missing tags OR collection OR PDF. Usable but hard to find.

4. **Report** grouped by severity — a table per bucket (key, title, what's missing) plus a
   summary line (N total, how many broken / auto-completable / need filing). Offer to save it
   to `outputs/zotero_audits/audit_YYYY-MM-DD.md`.

## `--fix` mode

Only for **Incomplete** items that have a DOI:
1. Fetch canonical metadata from Crossref (`https://api.crossref.org/works/{doi}`) via WebFetch.
2. Show the proposed change (field-by-field, before → after) and **wait for approval**.
3. On approval, apply it — via the Zotero MCP if your server supports writes, otherwise tell
   the user the exact value to paste into Zotero. Re-read the item to confirm the change landed.

- **Broken** items → flag for manual review only; never auto-fix.
- **Unorganized** items → skip; tagging and filing need human judgment.

## Rules

- **Never bulk-update without per-item approval** — show every proposed change first.
- **Don't invent tags.** `--fix` only fills DOI-derivable metadata.
- If Crossref returns multiple matches, flag the ambiguity — don't guess.
