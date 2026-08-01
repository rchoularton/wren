# Your research database

The kit doesn't force a database on you. Pick a tier by setting `database.backend` in `research-config.yml`, then re-run `./setup.sh`. Start at Tier 0 and move up only when you actually need to.

| Tier | `backend` | Server? | Best for |
|------|-----------|---------|----------|
| 0 | `files` | none | most projects; qualitative or small tabular data |
| 1 | `sqlite` / `duckdb` | none (local file) | structured tabular data, pandas/SQL queries |
| 2 | `directus-local` | Docker (localhost) | a full admin UI + API + MCP, self-hosted and free |
| 3 | `managed` | hosted | teams / production; any host you like |

---

## Tier 0 — files (default)

Put CSV / JSON / Markdown in `data/`. Record the canonical path of anything shared across scripts in `outputs/CANONICAL_PATHS.md`. No setup. This is where most people should start.

## Tier 1 — SQLite or DuckDB (local, single file)

A single database file lives in `data/` (git-ignored). DuckDB is excellent for analytical work and reads/writes pandas directly; SQLite is great for relational records.

```bash
pip install duckdb pandas        # or rely on Python's built-in sqlite3
python3 scripts/db/init_db.py    # creates data/research.duckdb from data/schema.example.json
```

Query from any script with the helper in `scripts/db/`. To let the assistant query it directly, add a community SQLite/DuckDB MCP server to `.mcp.json` (see `docs/integrations.md`).

## Tier 2 — self-hosted Directus (Docker) — the local mirror of a full CMS

Directus gives you a database + REST/GraphQL API + admin UI + a native MCP server, self-hosted for free. This is the closest local equivalent to a hosted research database.

```bash
# a docker-compose file is rendered from data/docker-compose.directus.yml.template
docker compose -f data/docker-compose.directus.yml up -d
# open http://localhost:8055  → create your admin account
```

Then:
1. In the Directus admin UI, create collections (start from `data/schema.example.json`).
2. Create a static access token (Settings → Access Tokens).
3. Put `DIRECTUS_URL=http://localhost:8055` and `DIRECTUS_TOKEN=…` in `.env`.
4. Set `database.backend: directus-local` and re-run `./setup.sh` — this wires the Directus MCP into `.mcp.json` so the assistant can read/write it (writes require your approval).

> All writes to a hosted/shared database require explicit approval (Safety Rule 1). Ask the assistant to *show* proposed changes one table at a time before saving.

## Tier 3 — managed (bring your own host)

Run Directus (or any backend) on a host you control — Railway, Render, Fly, Supabase, a VPS. Set `database.backend: managed` and `database.url`, put credentials in `.env`, and wire the MCP the same way. The kit is host-agnostic; the source system this was extracted from happened to use one such host, but nothing here depends on it.

### Deploying Directus to a host (sketch)

Most platforms take the official `directus/directus` Docker image plus a Postgres database and a couple of env vars (`KEY`, `SECRET`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `DB_*`). See the Directus self-hosting docs for your platform, then point `DIRECTUS_URL` at the deployed instance.
