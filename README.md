<p align="center"><img src="assets/logo/wren-128.png" width="128" alt="Wren logo"></p>

# Wren

[![npm version](https://img.shields.io/npm/v/create-wren)](https://www.npmjs.com/package/create-wren)
[![node](https://img.shields.io/node/v/create-wren)](https://nodejs.org)
[![license: MIT](https://img.shields.io/npm/l/create-wren)](LICENSE)

An agentic research assistant for [Claude Code](https://claude.com/claude-code) — the reusable scaffolding of a working PhD research system, generalised so you can point it at *your* field on day one.

It gives you a **memory that persists across sessions**, a **paper workflow** with a Markdown↔Word build engine and a gold-standard freeze gate, **behaviour rules** that keep the assistant rigorous, and a **pluggable data + reference layer** — with **no external service required** to start.

> Extracted and genericised from a disaster-risk-finance research system. All domain content, identity, hosting choices, and secrets have been stripped; you supply your own via one config file.

![Wren in the terminal — scaffold a project, then drive it from Claude Code](assets/demo.gif)

📖 **Full documentation:** <https://rchoularton.github.io/wren/>

---

## How it fits together

```mermaid
flowchart LR
    S["npm create<br/>wren"] --> P["your project<br/>research-config.yml"]
    P --> CC["Claude Code<br/>drives everything from the terminal"]
    CC --> M["4-layer memory<br/>rules · session · corpus · per-paper"]
    CC --> W["paper workflow<br/>Markdown ⇄ Word · freeze gate"]
    CC --> D["pluggable data + references<br/>files → SQLite/DuckDB/Directus · BibTeX/Zotero"]
```

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
npm create wren@latest my-research
cd my-research
# answer ~11 prompts → writes research-config.yml, renders templates, installs hooks, inits git
```

Already cloned this repo instead?

```bash
cp research-config.example.yml research-config.yml   # edit a handful of fields
./setup.sh
```

Then open the folder in Claude Code and run `/setup wren` — a guided tour that interviews you, sets up the right tools, and starts your first paper. (Prefer to jump in? Run `/paper`.) See **[QUICKSTART.md](QUICKSTART.md)** for the full first-run walkthrough, or the [Getting Started guide](https://rchoularton.github.io/wren/getting-started/).

---

## Skills

Type these in Claude Code once the project is open. All 12 ship in the box:

| | |
|---|---|
| **Orient & manage** | `/research` (workspace entry point) · `/paper` (portfolio: status, resume, start a paper) · `/setup wren` (guided onboarding) · `/setup` (reconfigure) |
| **Write & submit** | `/draft` (analysis → prose) · `/cover-letter` · `/revision-response` · `/ref-check` (validate citations) · `/peer-review` · `/figure` (figure design → critique loop) |
| **Discover** | `/literature-scan` (recent work, scooping risk, citation gaps) · `/zotero-audit` (library hygiene) |
| **Rigor & memory** | `/gold-standard` (Phase-7 freeze) · `/qc-team` (3-agent adversarial QC) · `/rigor-check` (mid-task self-audit) · `/methods-audit` (script QC) · `/research-memory` (query/log corpus memory) · `/retro` (capture a learning) |

As of 0.7 the sub-agent tier ships, and with it `/qc-team` and `/figure`. What's next is on the [roadmap](https://rchoularton.github.io/wren/roadmap/).

---

## Configuration

One file — `research-config.yml` — makes the kit yours: your name, a project namespace, your database backend, your reference manager, and which optional tiers to install. It is git-ignored, so your identity and paths never get committed. Secrets live only in `.env`. Re-run `./setup.sh` any time to apply edits.

See [`research-config.example.yml`](research-config.example.yml) for every field.

---

## Tiers

- **Core** (installs by default, zero external services): memory architecture, paper template + build engine, rules, hooks, notifications, the BibTeX reference adapter, the file-based data tier, and the writing/discovery skills above.
- **Corpus memory** (shipped, opt-in): a two-layer episodic + semantic memory over your literature and projects.
- **Config-selectable backends**: local/managed databases (`docs/database.md`) and reference managers including Zotero (`docs/integrations.md`).
- **Token-aware** (as of 0.7): model-routing tiers + a `npm run tokens` usage report, so cheap work runs on cheap models.
- **Planned** (see [`ROADMAP.md`](ROADMAP.md)): weekly library tooling, scheduled background jobs, a second-brain memory lens, and multi-author collaboration.

Full guides on the [documentation site](https://rchoularton.github.io/wren/).

---

## Requirements

- [Claude Code](https://claude.com/claude-code) (new to it? see [Getting Started](https://rchoularton.github.io/wren/getting-started/))
- Node ≥ 18 and Python ≥ 3.9
- macOS or Linux (scheduled jobs and desktop notifications are macOS-first; Linux uses cron and degrades notifications gracefully)
- Optional: Docker (for the local Directus database tier), a reference manager

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Good first contributions include porting the planned skills and adding database/reference adapters.

## License

MIT — see [LICENSE](LICENSE).
