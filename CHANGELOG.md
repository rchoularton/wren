# Changelog

All notable changes to `create-research-assistant` are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versions are integer-ish semver.

## [0.2.0] — 2026-08-01

Fixes a scaffold-time install failure reported on a real machine, hardens the
setup pipeline, and ships four writing skills.

### Fixed
- **Install no longer fails at verify.** `scrub_check` (a maintainer publish gate)
  was running as a hard check during a user's install; with no git repo in the
  fresh project it scanned the gitignored `research-config.yml` and flagged the
  user's own home path. Removed it from `verify_install`; the scaffolder now runs
  `git init`; and `scrub_check`'s no-git fallback excludes rendered/user files.
- **PyYAML bootstrap** in `setup.sh` no longer aborts on PEP-668
  "externally-managed" Python — it tries `--user` / `--break-system-packages` and
  prints clear guidance instead of hard-failing.
- **Config writing is YAML-safe.** Interactive answers containing quotes,
  backslashes, or newlines no longer produce invalid `research-config.yml`.
- **`paper:build` / `paper:extract`** now print a clear "run `npm run paper:setup`"
  message when `python-docx` / `markdown` aren't installed, instead of a traceback;
  QUICKSTART documents the one-time `paper:setup` step.
- **Memory slug** now matches Claude Code's real project-dir encoding (all
  non-alphanumerics → `-`), so cross-session memory loads for project paths that
  contain spaces or other punctuation. Single shared sanitizer across the scripts.

### Added
- Four writing skills, genericised from the source system:
  `/cover-letter`, `/revision-response`, `/peer-review`, `/literature-scan`.
  These make the drafting → submission phases of the pipeline real.

### Changed
- Docs are honest about what ships: `/qc-team` and `/figure` are labelled
  **planned** (not live pipeline steps); removed the dead `qc_suite` /
  `figure_suite` / `librarian` config flags that nothing consumed.
- Made the external-sync wording in `paper:status` provider-neutral (the sync
  folder is optional; it previously named one cloud provider).

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
