# Changelog

All notable changes to `create-research-assistant` are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versions are integer-ish semver.

## [0.1.0] — 2026-08-01

Initial public release. A generic, agentic research assistant for Claude Code,
extracted and genericised from a disaster-risk-finance research system with all
domain content, identity, hosting choices, and secrets stripped.

### Added
- **`npm create research-assistant` scaffolder** — copies the kit into a new project
  directory, prompts for the handful of fields that make it yours, writes
  `research-config.yml`, then renders templates + installs hooks via the Python renderer.
- **Config-driven templating** — `research-config.yml` drives `CLAUDE.md` /
  `CLAUDE_REFERENCE.md` / `.mcp.json` rendering; conditional MCP blocks per the
  chosen data and reference backends.
- **Paper workflow** — Markdown⇄Word build/extract engine, per-paper `STATUS.md`,
  and the `paper:*` npm scripts.
- **Corpus-memory tier** (`tiers.research_memory`) — a two-layer episodic + semantic
  memory over your literature and projects, with:
  - `memory:bootstrap` — idempotent scaffolder/repair for the memory tree.
  - `memory:audit` — offline health/completeness check (JSON log + severity findings).
- **Behavior rules, hooks, and skills** — the rigor/tooling/one-at-a-time rule set,
  session hooks, and the core skills (paper, draft, gold-standard, research-memory,
  research, retro).
- **Pluggable backends** — database (files / SQLite / DuckDB / local Directus / managed)
  and reference manager (BibTeX / Zotero / Mendeley) selected at setup.
- **Safety** — a secret-scrub gate (`setup:scrub-check`) and protected-write-path guards.

### Requirements
- Node.js ≥ 18 (scaffolder is zero-dependency).
- Python ≥ 3.9 on PATH (template renderer; auto-installs PyYAML on first run).

### Not yet shipped (see `ROADMAP.md`)
- Automated corpus-memory ingestion (the Zotero-coupled nightly engine).
- Scheduled headless jobs, the QC/figure/peer-review agent suites, and a local database tier.
