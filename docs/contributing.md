# Contributing

Issues and PRs are welcome. Full contributor setup and workflow details live in [`CONTRIBUTING.md`](https://github.com/rchoularton/wren/blob/main/CONTRIBUTING.md) at the repo root — that file is the canonical reference; this page just points you there.

## Good first contributions

- **Planned roadmap items** — the next work is in the Planned table of the [Roadmap](roadmap.md): `/claim-audit`, `/code-capsule`, journal-submission-prep and reference-manager agents, and `/consistency-check` (0.13), then the later releases listed there.
- **Adding database or reference adapters** — a community SQLite/DuckDB MCP, a Mendeley REST API wrapper (see [References & integrations](guides/references.md)), or support for another backend tier.
- **Building the automated corpus-memory ingestion engine** — the Zotero-coupled nightly job described in [Corpus memory](guides/corpus-memory.md#the-automated-zotero-ingestion-module-future-advanced) is documented but intentionally not shipped in v1.
- **Scheduled jobs tooling** — headless nightly/weekly tasks (notifications, digests), per `research-config.yml`'s `scheduler` block.

See the [Roadmap](roadmap.md) for the full list of add-on modules under consideration.

## Running the tests

Hook and script tests live in `tests/` and use [pytest](https://docs.pytest.org/). They are contributor-only: the scaffolder does not copy `tests/` or `requirements-dev.txt` into a new project.

```bash
python3 -m pip install -r requirements-dev.txt
npm run test
```

Two other checks run from npm scripts:

- `npm run context:size` reports the size (bytes and estimated tokens) of the standing context Wren loads every session: the `CLAUDE.md` template, the rules, the memory seed, agent descriptions and the SessionStart hook injections.
- `npm run audit:models` fails if a model reference has drifted from `.claude/lib/model-policy.mjs`: an agent's `model:` value outside the policy aliases, a literal model id not in the policy, or an outdated id.

`tests/conftest.py` provides two fixtures: `run_hook(path, event, env)` runs a `.py` or `.sh` hook as a subprocess with the event JSON on stdin and returns the exit code, stdout, stderr and parsed JSON; `scaffold_project` builds a temp project root (path containing a space) to point `CLAUDE_PROJECT_DIR` at. CI runs the same `npm run test` after the byte-compile step.
