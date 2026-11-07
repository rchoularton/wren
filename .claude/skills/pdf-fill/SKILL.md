---
name: pdf-fill
description: Attach missing PDFs to a paper's Zotero collection from Unpaywall, OpenAlex and publisher meta tags; dry run first, then apply; leftovers go to a manual list
user-invocable: true
argument-hint: "<paper-id> [--keys K1,K2] [--only unpaywall|openalex|sniff]"
---

# PDF Fill

Find the items in a paper's Zotero collection that have no PDF and attach one from an open-access source. Use it before a submission or revision, when reviewers expect every cited item on file.

**Requires** `references.provider: zotero` in `research-config.yml`, with `ZOTERO_API_KEY` and `ZOTERO_LIBRARY_ID` in `.env`. On any other provider, stop and say so. `UNPAYWALL_EMAIL` in `.env` enables the Unpaywall source; without it that source is skipped with a notice.

## Usage

```
/pdf-fill my-paper
/pdf-fill my-paper --only openalex
/pdf-fill my-paper --keys ABCD1234,EFGH5678
```

## What to do

1. **Find the collection.** The key is `zotero_collection` in `papers/<id>/config.json` (the 8 characters at the end of the collection's Zotero web URL, `/collections/<KEY>`). If it is empty, ask the user for the key (one question), or run with `--collection KEY`. Do not guess.
2. **Dry run first** (default, writes nothing):
   ```bash
   npm run pdf:fill -- <paper-id>
   ```
   Pass `--keys` and `--only` through if the user gave them. Show the summary line (`found / attached / manual / failed`) and the manual list.
3. **Ask ONE question:** apply the N attachable PDFs to Zotero? Wait for the answer.
4. **On yes, apply:**
   ```bash
   npm run pdf:fill -- <paper-id> --apply
   ```
   The script uploads each PDF, then re-reads the item's children to confirm it landed (a 204 is not proof). Report the counts it prints, and any `failed` items with their error.
5. **Leftovers.** Items not found in an open source are written to `outputs/pdf-fill/<paper-id>-manual.md` as DOI links. If `INSTITUTION_PROXY_PREFIX` is set in `.env`, the links go through that proxy. The user opens them, downloads the PDFs and attaches them in Zotero. There is no browser automation.

## Safety

- Dry run is the default; only `--apply` writes to Zotero.
- Every download must start with `%PDF` and be under 50 MB.
- Items that already have an uploaded PDF are skipped.
- The JSONL log is `outputs/pdf-fill/<paper-id>-<date>.jsonl`.

## Related

- `npm run zotero:reparent -- <plan.json>` repairs parentless attachments (dry run by default; `--apply` writes and re-reads each change).
- Build or fix the collection itself with `/zotero-audit`; check citations with `/ref-check`.
- Scripts and env vars: `scripts/zotero/README.md`.
