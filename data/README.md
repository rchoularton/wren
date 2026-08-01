# Data

Where your research data lives. What goes here depends on your `database.backend` (set in `research-config.yml`):

- **`files`** (default) — put CSV / JSON / Markdown datasets directly in this folder. No server, no setup. Great for qualitative work or small tabular data. Use `outputs/CANONICAL_PATHS.md` to record the source-of-truth path for anything shared across scripts.
- **`sqlite` / `duckdb`** — a single local database file (git-ignored) lives here. See `docs/database.md`.
- **`directus-local`** — a self-hosted Directus (Docker) holds your structured data; this folder is just for exports/imports. `data/docker-compose.directus.yml` (rendered from the template) brings it up at `localhost:8055`.
- **`managed`** — data lives in your hosted backend; this folder is for local working copies.

See `data/schema.example.json` for a small starter schema, and `docs/database.md` for the full guide.
