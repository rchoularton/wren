# Research Assistant Starter Kit

An agentic research assistant for [Claude Code](https://claude.com/claude-code) — the reusable scaffolding of a working PhD research system, generalised so you can point it at *your* field on day one.

It gives you a **memory that persists across sessions**, a **paper workflow** with a Markdown↔Word build engine and a gold-standard freeze gate, **behaviour rules** that keep the assistant rigorous, and a **pluggable data + reference layer** — with **no external service required** to start.

> Extracted and genericised from a disaster-risk-finance research system. All domain content, identity, hosting choices, and secrets have been stripped; you supply your own via one config file.

---

## What you get

| | |
|---|---|
| **Four-layer memory** | Behaviour rules · cross-session context · corpus memory · per-paper deep work — each with one home and a boundary rule so nothing lands in the wrong place. |
| **Paper workflow** | A per-paper template (`STATUS`/`PLAN`/`METHODS_LOG`/`NOTES` + drafts/figures/reviews) and a build engine that round-trips Markdown ⇄ Word. A 14-phase pipeline with a **gold-standard freeze gate** (no drafting on un-frozen analysis). |
| **Self-improving loop** | `/retro` captures a learning at session end; a SessionStart hook resurfaces recent learnings; recurring feedback gets promoted into an always-on rule. |
| **Pluggable data** | Start with files (zero setup). Grow into local SQLite/DuckDB, a free self-hosted Directus (Docker, with its own MCP + admin UI), or any managed host. |
| **Pluggable references** | Universal BibTeX/CSL-JSON adapter works with *any* manager. Opt into live Zotero via MCP. Mendeley supported via `.bib` export. |
| **Ambient signals** | Long jobs post macOS notifications and log to `RUNNING.md`; degrade gracefully off macOS. |

**Nothing in the core needs Zotero, a database, a scheduler, or any account.** Those are opt-in modules you enable in one config file.

---

## Quick start (≈15 minutes)

```bash
npm create research-assistant@latest my-research
cd my-research
# answer ~8 prompts → writes research-config.yml, renders templates, installs hooks
```

Already cloned this repo instead?

```bash
cp research-config.example.yml research-config.yml   # edit ~8 fields
./setup.sh
```

Then open the folder in Claude Code and run `/paper`. See **[QUICKSTART.md](QUICKSTART.md)** for the full first-run walkthrough.

---

## Configuration

One file — `research-config.yml` — makes the kit yours: your name, a project namespace, your database backend, your reference manager, and which optional tiers to install. It is git-ignored, so your identity and paths never get committed. Secrets live only in `.env`. Re-run `./setup.sh` any time to apply edits.

See [`research-config.example.yml`](research-config.example.yml) for every field.

---

## Tiers

- **Core** (installs by default, zero external services): memory architecture, paper template + build engine, rules, hooks, notifications, the BibTeX reference adapter, the file-based data tier, and the writing skills (`/draft`, `/cover-letter`, `/revision-response`, `/peer-review`, `/literature-scan`, `/gold-standard`).
- **Corpus memory** (shipped, opt-in): a two-layer episodic + semantic memory over your literature and projects.
- **Config-selectable backends**: local/managed databases (`docs/database.md`) and reference managers including Zotero (`docs/integrations.md`).
- **Planned** (see [`ROADMAP.md`](ROADMAP.md)): the QC (`/qc-team`) and figure-design (`/figure`) agent suites, weekly library tooling, and scheduled background jobs.

See [`docs/`](docs/) for the database and integrations guides.

---

## Requirements

- [Claude Code](https://claude.com/claude-code)
- Node ≥ 18 and Python ≥ 3.9
- macOS or Linux (scheduled jobs and desktop notifications are macOS-first; Linux uses cron and degrades notifications gracefully)
- Optional: Docker (for the local Directus database tier), a reference manager

## License

MIT — see [LICENSE](LICENSE).
