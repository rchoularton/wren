# Configuration

One file — `research-config.yml` — makes the kit yours: your name, a project namespace, your database backend, your reference manager, and which optional tiers to install. It is **git-ignored**, so your identity and paths never get committed. Secrets never live here at all; they go in `.env`.

The scaffolder generates `research-config.yml` from your setup answers; edit that file (not `research-config.example.yml`, which is the reference template) and re-run `./setup.sh` any time to apply changes — it re-renders `CLAUDE.md`, `CLAUDE_REFERENCE.md`, and `.mcp.json` from the new values.

## `identity`

```yaml
identity:
  author_name: "Jane Researcher"      # used in generated docs and agent context
  orcid: ""                           # optional, e.g. 0000-0000-0000-0000
  email: ""                           # used only for self-addressed digest drafts
  coauthors: []                       # e.g. ["A. Colleague", "B. Advisor"]
```

## `project`

```yaml
project:
  name: "My Research Assistant"       # human-facing project title
  namespace: "myresearch"             # lowercase, no spaces. Derives launchd
                                      # labels (com.myresearch.*), the notify
                                      # group, and cron job names.
  discipline: "one-line plain description of your field"
  root: ""                            # auto-detected (git repo root); leave blank
```

`root` is used to derive the Claude Code per-project memory slug — leave it blank and let the scaffolder detect it.

## `domain`

```yaml
domain:
  key_terms: []                       # e.g. ["term A", "term B"]
```

Vocabulary the assistant should treat as first-class terms in your field.

## `journals`

```yaml
journals:
  default: "Target Journal"           # seeds the journal-agnostic agent templates
  targets: []                         # e.g. ["Journal One", "Journal Two"]
```

## `paths`

```yaml
paths:
  protected_write_paths: []           # e.g. ["~/OneDrive/Manuscripts"]
```

'Never overwrite' locations the pre-write safety guard should protect. Use absolute paths or `~` home-relative. Leave empty for none.

## `database`

```yaml
database:
  backend: files
  url: ""                             # required only for `managed`
```

`backend` options (see [Databases](guides/databases.md) for the full walkthrough of each):

| Value | Tier | Server? |
|---|---|---|
| `files` | 0 (default) | none — Markdown/CSV/JSON in `data/` |
| `sqlite` | 1 | none — single-file local DB + query helper |
| `duckdb` | 1 | none — analytical single-file DB, pandas-friendly |
| `directus-local` | 2 | Docker (localhost:8055) — self-hosted, free, ships its own MCP server + admin UI |
| `managed` | 3 | hosted — bring-your-own backend (Railway/Supabase/…) |

## `references`

```yaml
references:
  provider: bibtex
  bibtex_path: "references/library.bib"
  zotero:
    user_id: ""
    api_key_env: "ZOTERO_API_KEY"     # name of the env var in .env, never the key itself
```

`provider` options (see [References & integrations](guides/references.md)):

| Value | Notes |
|---|---|
| `bibtex` (default) | Point at a `.bib` / CSL-JSON / RIS file exported from **any** manager (Zotero, Mendeley, EndNote, Paperpile). Zero external service. |
| `zotero` | Opt-in richer adapter via the community `zotero-mcp` server (live library, full text, PDFs). Needs `zotero.user_id` + `ZOTERO_API_KEY`. |
| `mendeley` | Mendeley has a REST API but no turnkey MCP. Use `bibtex` (export a `.bib`) for now. |

## `integrations`

```yaml
integrations:
  gmail:
    enabled: false                    # weekly digest drafts (needs Gmail MCP connected)
```

## `scheduler`

```yaml
scheduler:
  platform: launchd                   # launchd (macOS) | cron (Linux) | none
  jobs:
    nightly_memory:
      enabled: false
      at: "02:30"
    weekly_digest:
      enabled: false
      day: "Mon"
      at: "08:47"
```

Optional add-on module for headless scheduled jobs (nightly memory tasks, weekly digests). See the roadmap — full scheduled-jobs tooling is a planned module.

## `notifications`

```yaml
notifications:
  enabled: true                       # macOS terminal-notifier; auto-off elsewhere
```

## `tiers`

```yaml
tiers:
  research_memory: true               # two-layer corpus memory engine (grep-queryable)
```

Toggles the [corpus memory](guides/corpus-memory.md) add-on.

---

See [`research-config.example.yml`](https://github.com/rchoularton/wren/blob/main/research-config.example.yml) in the repo for the fully-commented reference file this page is generated from.
