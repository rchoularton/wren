# Contributing

Issues and PRs are welcome. Full contributor setup and workflow details live in [`CONTRIBUTING.md`](https://github.com/rchoularton/wren/blob/main/CONTRIBUTING.md) at the repo root — that file is the canonical reference; this page just points you there.

## Good first contributions

- **Porting the planned skills** — `/qc-team` (adversarial QC) and `/figure` (figure design/critique) are documented in [Skills](skills.md#planned-not-shipped) and [`ROADMAP.md`](roadmap.md) but not yet built.
- **Adding database or reference adapters** — a community SQLite/DuckDB MCP, a Mendeley REST API wrapper (see [References & integrations](guides/references.md)), or support for another backend tier.
- **Building the automated corpus-memory ingestion engine** — the Zotero-coupled nightly job described in [Corpus memory](guides/corpus-memory.md#the-automated-zotero-ingestion-module-future-advanced) is documented but intentionally not shipped in v1.
- **Scheduled jobs tooling** — headless nightly/weekly tasks (notifications, digests), per `research-config.yml`'s `scheduler` block.

See [`ROADMAP.md`](roadmap.md) for the full list of add-on modules under consideration.

## Running the tests

Hook and script tests live in `tests/` and use [pytest](https://docs.pytest.org/). They are contributor-only: the scaffolder does not copy `tests/` or `requirements-dev.txt` into a new project.

```bash
python3 -m pip install -r requirements-dev.txt
npm run test
```

`tests/conftest.py` provides two fixtures: `run_hook(path, event, env)` runs a `.py` or `.sh` hook as a subprocess with the event JSON on stdin and returns the exit code, stdout, stderr and parsed JSON; `scaffold_project` builds a temp project root (path containing a space) to point `CLAUDE_PROJECT_DIR` at. CI runs the same `npm run test` after the byte-compile step.
