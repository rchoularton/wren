# scripts/zotero

Dependency-free Zotero tooling (Node 18+, built-in `fetch`). Use it with `references.provider: zotero`.

## Environment (`.env`, loaded by the scripts themselves)

| Variable | Purpose |
|---|---|
| `ZOTERO_API_KEY` | Required. Key with write access (https://www.zotero.org/settings/keys). |
| `ZOTERO_LIBRARY_ID` | Required. Numeric user id, or group id. |
| `ZOTERO_LIBRARY_TYPE` | Optional. `user` (default) or `group`. |
| `UNPAYWALL_EMAIL` | Contact email for Unpaywall (also used as the OpenAlex polite-pool address). Unset: Unpaywall is skipped with a notice. |
| `INSTITUTION_PROXY_PREFIX` | Optional. A proxy URL prefix put before each DOI link in the manual list. No browser automation. |

`.env` is read from `$CLAUDE_PROJECT_DIR`, else the repo root. Variables already in the environment win.

## Scripts

- `pdf-fill.mjs` (`npm run pdf:fill -- <paper>`): for a paper's collection (`zotero_collection` in `papers/<id>/config.json`, or `--collection KEY`), finds items without a PDF, tries Unpaywall, OpenAlex, then publisher meta-tag sniff, attaches the first valid PDF and verifies by re-reading. Dry run by default; `--apply` writes. Flags: `--keys K1,K2`, `--only unpaywall|openalex|sniff`. Writes `outputs/pdf-fill/<paper>-manual.md` and a JSONL log on `--apply`.
- `reparent-orphan-attachments.mjs` (`npm run zotero:reparent -- <plan.json>`): plan-driven repair of parentless attachments (create parent, attach to existing parent, or trash). Dry run by default; `--apply` writes, re-reads each change, and logs to JSONL. Re-runs skip attachments already logged.
- `approval-queue.mjs` (`npm run zotero:queue -- <command> ...`): review and apply an approval queue (schema below). Commands: `status <file>`, `approve <id> <file> [--retry]`, `approve-all <file>`, `reject <id> <file> [reason]`, `skip <id> <file> [reason]`, `reconcile <file> [--apply] [--include-manual] [--verbose]`. Exit codes: 0 success, 1 bad arguments or file, 2 Zotero API error or a failed action.
- `build-queue.mjs` (`npm run zotero:build-queue -- --date YYYY-MM-DD [--dir outputs/librarian] [--out <file>] [--force]`): the deterministic step between the librarian agents and the queue. Reads every `*_<date>.proposals.json` in the directory (`{agent, generated, actions}`, actions without `id` or `status`), validates each action (known type; per-type `details` as in the table below; placeholder values refused with the same check `approval-queue.mjs` uses; `add_item` needs a title or DOI; `fix_metadata` needs `item_key` and at least one change; DOIs normalised), drops duplicates (same DOI; same `item_key` + field; same `item_key` + tag; same `item_key` + collection; the first wins), assigns ids from 1, sets every `status` to `pending`, records `source_agent`, and writes `approval_queue_<date>.json` atomically. Rejected proposals, dropped duplicates and unreadable files are written with reasons to `rejected_<date>.json`. An existing queue for that date is not overwritten without `--force`, and `--force` refuses if any action in it is no longer `pending`. No network. It accepts `add_item`, `fix_metadata`, `add_tag`, `add_to_collection` and `merge_duplicate` (`keep` plus a non-empty loser list, keeper not among them; deduplicated on keeper plus sorted losers). DOIs must match `10.<4-9 digits>/<suffix>` after normalisation, under any key spelling and inside `field_fixes` or flat `field`/`proposed`, or the action is rejected. `add_item.authors` must be an array. Duplicates are dropped per field (`fix_metadata`: other fields of the action are kept) and per tag (case-insensitive, trimmed). Exit 0 on success (even with rejections); exit 0 with "no actions proposed" and no queue file when every proposals file parses but nothing was accepted (rejections are still written to `rejected_<date>.json`); exit 1 on argument or file errors, when no readable proposals file exists, or when no proposals file exists for the date.
- `detect-duplicates.mjs` (`npm run zotero:duplicates [-- --out outputs/librarian/duplicates.json --limit N --no-fuzzy]`): read-only report of likely duplicates, grouped by exact DOI (lower-cased, `https://doi.org/` stripped), then by fuzzy title (Jaro-Winkler >= 0.92). The fuzzy pass compares only candidate pairs: two shared title tokens (length >= 4, minus stopwords), or one shared token of length >= 8, each with lengths within 20 percent, or titles that start with the same 12 characters. That trades some recall for speed (a pair meeting none of these rules is never compared, and a pair still needs Jaro-Winkler >= 0.92); `--no-fuzzy` skips the title pass for DOI-only grouping. Progress goes to stderr. Issues only GET requests.
- `_lib/dup-match.mjs`: title normalisation and Jaro-Winkler, shared by the duplicate report and the merge check.
- `_lib/crossref-item.mjs`: Crossref work -> Zotero item typed by the work's own `type` (journal article, book chapter, book, report, conference paper, preprint), setting only fields valid for that Zotero type. Crossref is fetched through an injectable `fetch`.
- `_lib/zotero-client.mjs`: the client (`createClient({fetch, env})`): URLs, headers, 412/403/429 handling, `attachPdfToItem`, `.env` parser.
- `sources/`: `unpaywall.mjs`, `openalex.mjs`, `publisher-sniff.mjs`, and `download.mjs` (requires `%PDF` magic bytes, caps size at 50 MB).

## Approval queue

Queue files and duplicate reports live in `outputs/librarian/`. A queue is a JSON file; nothing in it touches Zotero until an action is approved. See `examples/approval-queue.example.json`.

Top level: `date` (YYYY-MM-DD), optional `source` (free text), `actions` (array).

Per action: `id` (integer, unique in the file), `type`, `status`, `title` (one line for humans), optional `paper` (paper id, used in the `source-<paper>` tag), `details` (object, per type below). The scripts add: `decided_at`, `reason` (reject/skip), `applied_at`, `result`, `failed_at`, `error`, `created_key` (`add_item`: key of the item once the create succeeded), `reconciled_at`, `reconciled_note`, `reconcile_error`.

| Type | `details` |
|---|---|
| `add_item` | `doi` and/or `title`, `authors` (strings or `{given, family}`), `venue`, `date`, `abstract`, `url`, `relevance` (`high`/`medium`/`low`). With a DOI the item is typed and populated from Crossref; the proposer's fields are the fallback (no DOI, Crossref unreachable, or unmapped type). Tags added: `librarian-team`, `source-<paper>`, `relevance-<level>`. |
| `fix_metadata` | `item_key` plus `proposed_changes` `{field: value}`, or `field_fixes` `[{field, proposed}]`, or flat `field` + `proposed`. Friendly names (`abstract`, `journal`, `doi`, `authors`) are mapped to Zotero fields. Placeholder values (empty, `unknown`, `n/a`, `TBD`, "fetch from Crossref"...) are refused and the action fails. Fields not valid for the item's type are dropped with a warning (`result.warnings`); if none are left the action fails. |
| `add_tag` | `item_key`, `tags` (array of strings). |
| `add_to_collection` | `item_key`, `collection_key`. |
| `merge_duplicate` | `keep` and `merge_keys` (array), or `keep` + `merge`/`remove`. The keeper gains the losers' tags and collections and a `dc:replaces` relation; the losers' child items move to the keeper; the losers go to the Zotero trash (reversible), never a hard delete. |

`merge_duplicate` refuses, before any change, a keeper listed among the items to merge away, an empty set, and any loser that is not the same item type as the keeper with an equal DOI or a title similarity >= 0.92. `add_item` and `fix_metadata` also refuse placeholder creator names, and bracketed values such as `[no title]`, `[unknown]`, `[n.d.]`; `add_item` refuses an empty title.

Any other type (for example `flag_*`) has no executor; `reconcile --apply` parks it as `needs-manual`.

Status lifecycle: `pending` -> `approved` | `rejected` | `skipped` -> `applied` | `failed`. `approve <id>` runs an action that is `pending`, `approved` or `failed`; `approve-all` runs only `approved` ones. Action ids are whole numbers (`1abc` is an argument error). Re-running `approve` on a `failed` action needs `--retry`; an `add_item` that already recorded `created_key` is verified and adopted rather than created again, and without one the library is searched for the DOI first. `reconcile` checks `pending`/`approved` actions against the live library and, with `--apply`, marks verified ones `already_done` and unresolvable ones `needs-manual` (a dry run writes nothing). For `fix_metadata`, `already_done` needs the current value to equal the proposed one (trimmed, case-insensitive, whitespace-collapsed); a different non-empty value is reported in a `differs` bucket and the action stays `pending`. `reconcile` exits 2 if any action errored. `applied` means the change was re-read from Zotero and matched; a mismatch is `failed` with the reason in `error`. Writes carry the item version, so a concurrent edit gives a 412 and a `failed` action. The queue file is rewritten atomically (temp file, then rename) after every decision and after each action of `approve-all`. Commands that write the queue (`approve`, `approve-all`, `reject`, `skip`, `reconcile --apply`) hold `<queue>.lock` (pid and ISO time, created exclusively) for their whole run; a second command exits 1 with "queue is locked by pid N since T". A lock older than 30 minutes is treated as stale and replaced with a warning. `status` and a dry-run `reconcile` take no lock.

### If a merge stops partway

`merge_duplicate` updates the keeper first (tags, collections, `dc:replaces`), then moves each loser's children and trashes the loser, re-reading after each step. If a step fails, the action is `failed`: the keeper is already updated, losers handled earlier are in the Zotero trash (restorable there), and the rest are untouched. Check the library before using `approve <id> --retry`.

`add_item` looks for its DOI in the library before creating anything (on any status) and adopts an existing non-trashed match. If the queue cannot be saved right after a create, the script prints the new item's key and the line to add (`"created_key": "<KEY>"`) to that action, then exits 2.

## Tests

`tests/test_zotero_scripts.py` and `tests/test_librarian_scripts.py` inject a fake fetch through `WREN_FAKE_FETCH=<path>` (see `tests/node/fake-fetch.mjs`). That variable is test-only; do not set it in real use. No test reaches the network.
