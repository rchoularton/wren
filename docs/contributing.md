# Contributing

Issues and PRs are welcome. Full contributor setup and workflow details live in [`CONTRIBUTING.md`](https://github.com/rchoularton/create-research-assistant/blob/main/CONTRIBUTING.md) at the repo root — that file is the canonical reference; this page just points you there.

## Good first contributions

- **Porting the planned skills** — `/qc-team` (adversarial QC) and `/figure` (figure design/critique) are documented in [Skills](skills.md#planned-not-shipped) and [`ROADMAP.md`](roadmap.md) but not yet built.
- **Adding database or reference adapters** — a community SQLite/DuckDB MCP, a Mendeley REST API wrapper (see [References & integrations](guides/references.md)), or support for another backend tier.
- **Building the automated corpus-memory ingestion engine** — the Zotero-coupled nightly job described in [Corpus memory](guides/corpus-memory.md#the-automated-zotero-ingestion-module-future-advanced) is documented but intentionally not shipped in v1.
- **Scheduled jobs tooling** — headless nightly/weekly tasks (notifications, digests), per `research-config.yml`'s `scheduler` block.

See [`ROADMAP.md`](roadmap.md) for the full list of add-on modules under consideration.
