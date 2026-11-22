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
- `approval-queue.mjs` (`npm run zotero:queue -- <command> ...`): review and apply an approval queue (schema below). Commands: `status <file>`, `approve <id> <file>`, `approve-all <file>`, `reject <id> <file> [reason]`, `skip <id> <file> [reason]`, `reconcile <file> [--apply] [--include-manual] [--verbose]`. Exit codes: 0 success, 1 bad arguments or file, 2 Zotero API error or a failed action.
- `detect-duplicates.mjs` (`npm run zotero:duplicates [-- --out outputs/librarian/duplicates.json --limit N]`): read-only report of likely duplicates, grouped by exact DOI (lower-cased, `https://doi.org/` stripped), then by fuzzy title (Jaro-Winkler >= 0.92). Issues only GET requests.
- `_lib/crossref-item.mjs`: Crossref work -> Zotero item typed by the work's own `type` (journal article, book chapter, book, report, conference paper, preprint), setting only fields valid for that Zotero type. Crossref is fetched through an injectable `fetch`.
- `_lib/zotero-client.mjs`: the client (`createClient({fetch, env})`): URLs, headers, 412/403/429 handling, `attachPdfToItem`, `.env` parser.
- `sources/`: `unpaywall.mjs`, `openalex.mjs`, `publisher-sniff.mjs`, and `download.mjs` (requires `%PDF` magic bytes, caps size at 50 MB).

## Approval queue

Queue files and duplicate reports live in `outputs/librarian/`. A queue is a JSON file; nothing in it touches Zotero until an action is approved. See `examples/approval-queue.example.json`.

Top level: `date` (YYYY-MM-DD), optional `source` (free text), `actions` (array).

Per action: `id` (integer, unique in the file), `type`, `status`, `title` (one line for humans), optional `paper` (paper id, used in the `source-<paper>` tag), `details` (object, per type below). The scripts add: `decided_at`, `reason` (reject/skip), `applied_at`, `result`, `failed_at`, `error`, `reconciled_at`, `reconciled_note`, `reconcile_error`.

| Type | `details` |
|---|---|
| `add_item` | `doi` and/or `title`, `authors` (strings or `{given, family}`), `venue`, `date`, `abstract`, `url`, `relevance` (`high`/`medium`/`low`). With a DOI the item is typed and populated from Crossref; the proposer's fields are the fallback (no DOI, Crossref unreachable, or unmapped type). Tags added: `librarian-team`, `source-<paper>`, `relevance-<level>`. |
| `fix_metadata` | `item_key` plus `proposed_changes` `{field: value}`, or `field_fixes` `[{field, proposed}]`, or flat `field` + `proposed`. Friendly names (`abstract`, `journal`, `doi`, `authors`) are mapped to Zotero fields. Placeholder values (empty, `unknown`, `n/a`, `TBD`, "fetch from Crossref"...) are refused and the action fails. Fields not valid for the item's type are dropped with a warning (`result.warnings`); if none are left the action fails. |
| `add_tag` | `item_key`, `tags` (array of strings). |
| `add_to_collection` | `item_key`, `collection_key`. |
| `merge_duplicate` | `keep` and `merge_keys` (array), or `keep` + `merge`/`remove`. The keeper gains the losers' tags and collections and a `dc:replaces` relation; the losers' child items move to the keeper; the losers go to the Zotero trash (reversible), never a hard delete. |

Any other type (for example `flag_*`) has no executor; `reconcile --apply` parks it as `needs-manual`.

Status lifecycle: `pending` -> `approved` | `rejected` | `skipped` -> `applied` | `failed`. `approve <id>` runs an action that is `pending`, `approved` or `failed`; `approve-all` runs only `approved` ones. `reconcile` checks `pending`/`approved` actions against the live library and, with `--apply`, marks verified ones `already_done` and unresolvable ones `needs-manual` (a dry run writes nothing). `applied` means the change was re-read from Zotero and matched; a mismatch is `failed` with the reason in `error`. Writes carry the item version, so a concurrent edit gives a 412 and a `failed` action. The queue file is rewritten atomically (temp file, then rename) after every decision.

## Tests

`tests/test_zotero_scripts.py` and `tests/test_librarian_scripts.py` inject a fake fetch through `WREN_FAKE_FETCH=<path>` (see `tests/node/fake-fetch.mjs`). That variable is test-only; do not set it in real use. No test reaches the network.
