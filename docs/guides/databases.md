# Databases

The kit doesn't force a database on you. Pick a tier by setting `database.backend` in `research-config.yml`, then re-run `./setup.sh`. Start at Tier 0 and move up only when you actually need to.

| Tier | `backend` | Server? | Best for |
|------|-----------|---------|----------|
| 0 | `files` | none | most projects; qualitative or small tabular data |
| 1 | `sqlite` / `duckdb` | none (local file) | structured tabular data, pandas/SQL queries |
| 2 | `directus-local` | Docker (localhost) | a full admin UI + API + MCP, self-hosted and free |
| 3 | `managed` | hosted | teams / production; any host you like |

This mirrors the pluggable-backends diagram in [Concepts](../concepts.md#pluggable-backends). The full walkthrough for each tier — including the Docker Directus setup and MCP wiring — lives in [`docs/database.md`](../database.md), which stays the single source of truth for this content so it doesn't drift out of sync.
