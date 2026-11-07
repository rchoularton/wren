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
- `_lib/zotero-client.mjs`: the client (`createClient({fetch, env})`): URLs, headers, 412/403/429 handling, `attachPdfToItem`, `.env` parser.
- `sources/`: `unpaywall.mjs`, `openalex.mjs`, `publisher-sniff.mjs`, and `download.mjs` (requires `%PDF` magic bytes, caps size at 50 MB).

## Tests

`tests/test_zotero_scripts.py` injects a fake fetch through `WREN_FAKE_FETCH=<path>` (see `tests/node/fake-fetch.mjs`). That variable is test-only; do not set it in real use. No test reaches the network.
