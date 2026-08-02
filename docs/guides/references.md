# References & integrations

Everything external is opt-in and declared in `research-config.yml`. Secrets always live in `.env` and are referenced as `${VARS}` — never written into committed files.

Set `references.provider` to choose your reference manager. All citation-aware skills (`/draft`, `/cover-letter`, `/peer-review`, `/literature-scan`) read through one interface, so the provider is swappable without touching any skill:

| Provider | Setup | Notes |
|---|---|---|
| `bibtex` (default) | Export your library as BibTeX/CSL-JSON/RIS from any manager, save it to `references.bibtex_path` | Zero external service, works offline, works with **any** tool (Zotero, Mendeley, EndNote, Paperpile) |
| `zotero` (opt-in) | Community [`zotero-mcp`](https://github.com/54yyyu/zotero-mcp) server, API key + user id in `.env` | Live search, full text, PDFs |
| `mendeley` | Export as BibTeX, use the `bibtex` provider | No turnkey Mendeley MCP exists yet — see below |

You can also add any other MCP server — a SQLite/DuckDB connector, a filesystem MCP, or a domain-specific server for your field — via `.mcp.json.template` or `settings.local.json`.

The full setup steps for each provider (API keys, `.mcp.json` wiring, the Mendeley REST API caveat, and general MCP-server instructions) live in [`docs/integrations.md`](../integrations.md), which stays the single source of truth for this content so it doesn't drift out of sync.
