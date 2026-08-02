# Contributing

Thanks for considering a contribution to Wren. This is a
scaffolder for [Claude Code](https://claude.com/claude-code) — most of the "code" is
Markdown (skills, rules), a small Python renderer/setup pipeline, and a zero-dependency
Node scaffolder. You don't need deep Node or Python expertise to contribute; you do
need to actually scaffold a project and run it to check your change.

## Development setup

Requirements: **Node ≥ 18**, **Python ≥ 3.9**.

```bash
git clone https://github.com/rchoularton/wren.git
cd wren
```

There's nothing to `npm install` — the scaffolder (`bin/create-wren.mjs`) is
zero-dependency (Node built-ins only). The Python renderer needs one dependency:

```bash
python3 -m pip install -r requirements.txt
```

### Running the scaffolder against your local checkout

Two ways to exercise a change, depending on what you're testing:

**1. Scaffold a fresh project from your checkout** (tests `bin/create-wren.mjs`
end to end — the real path a user takes):

```bash
node bin/create-wren.mjs /tmp/test-project
cd /tmp/test-project
```

Answer the prompts (or add `--yes` / `-y` to accept every default non-interactively —
useful for scripting, and what CI uses). This copies the kit into the target directory,
writes `research-config.yml`, then runs `./setup.sh` for you.

**2. Iterate in place** (faster loop when you're only touching templates, rules, or
skills, not the scaffolder itself):

```bash
cp research-config.example.yml research-config.yml   # edit a handful of fields
./setup.sh
```

Either way, finish with:

```bash
npm run setup:verify
```

which checks config presence, rendered files, hook permissions, the memory-slug
directory, and the example paper — the same acceptance gate CI runs.

## Repo structure you'll touch most

- **Skills** — `.claude/skills/<name>/SKILL.md`. A skill is a single Markdown file:
  YAML frontmatter (`name`, `description`, `user-invocable`, optional `argument-hint`)
  followed by the instructions Claude Code follows when the skill runs. Look at
  `.claude/skills/retro/SKILL.md` or `.claude/skills/paper/SKILL.md` for the shape.
- **Rules** — `.claude/rules/*.md`. Always-on or path-scoped (via a `paths:` frontmatter
  list) behavioral guidance — see `.claude/rules/outputs.md` for a path-scoped example.
  Rules are instructions, not code; they bind by being read, not executed.
- **Hooks** — `.claude/hooks/*.py` / `*.sh`, wired up in `.claude/settings.json` and
  installed (made executable) by `scripts/setup/install_hooks.py`. Hooks fire on
  Claude Code lifecycle events (`SessionStart`, `Stop`, pre-write, etc.) — see
  `.claude/hooks/session-start-learnings.py` for a documented example. A hook must
  derive any path (project root, memory slug) at runtime — never hardcode a
  contributor's or user's machine path.
- **Setup pipeline** — `scripts/setup/`: `render_templates.py` (renders `*.template.*`
  → concrete files from `research-config.yml`), `install_hooks.py`, `verify_install.py`
  (the acceptance gate), `scrub_check.py` (maintainer-only publish gate — not part of a
  user's install; see its docstring).
- **Data & reference adapters** — `scripts/db/`, `scripts/references/bibtex.py`, and the
  conditional blocks in `.mcp.json.template`. See `docs/database.md` and
  `docs/integrations.md` for the tier/provider model these plug into.

## Porting a skill from the source DRF system

Several **planned** items (see `ROADMAP.md` and the README's Skills table — `/qc-team`,
`/figure`) exist as working skills in the disaster-risk-finance system this kit was
extracted from, but haven't been genericised yet. Porting one is a good first PR:

1. Start from the source skill's `SKILL.md` and strip anything domain-specific
   (DRF terminology, hardcoded paths, references to `papers/paper{N}` naming).
2. Replace domain-specific config reads with the equivalent `research-config.yml` key
   (project name, namespace, database backend, reference provider) — see how existing
   skills like `.claude/skills/draft/SKILL.md` read config-driven fields instead of
   assuming a fixed field/paper structure.
3. If the skill implies a new dependency (e.g. an agent-team pattern for `/qc-team`),
   say so explicitly in the skill's frontmatter/description rather than silently
   assuming the tier is installed — this kit's `tiers.*` flags in `research-config.yml`
   are how optional capability is declared.
4. Add the skill to the README's Skills table and move its ROADMAP.md line from
   "Planned" to done, with a changelog entry.
5. Scaffold a fresh project and try invoking the skill from Claude Code to confirm it
   reads its config correctly with no leftover domain assumptions.

Adding a new **database** or **reference** adapter follows the same shape: add the
backend/provider under its tier in `docs/database.md` / `docs/integrations.md`, wire
its conditional block into `.mcp.json.template`, and add any renderer logic it needs to
`scripts/setup/render_templates.py`.

## Testing your change

There's no unit-test suite (yet) — the acceptance gate is:

1. `node --check bin/create-wren.mjs` (and any other `.mjs` file you
   touched) — syntax sanity.
2. `python3 -m py_compile` over any Python file you touched.
3. Scaffold clean into a **new temp directory** and confirm `npm run setup:verify`
   exits 0. Also try a path **containing a space** (e.g. `/tmp/a b/proj`) — a real
   bug class in v0.1.0/v0.2.0 that CI now guards against (see `.github/workflows/ci.yml`).
4. If you touched a skill or rule, actually open the scaffolded project in Claude Code
   and invoke it.

CI (`.github/workflows/ci.yml`) runs steps 1–3 automatically on every PR across Node 18
and 20. Please run step 3 locally before opening a PR — see the PR template checklist.

## Good first issues

- Port `/qc-team` or `/figure` from the source system (see above).
- Add a database adapter (e.g. a community SQLite/DuckDB MCP wired into
  `.mcp.json.template`, per `docs/database.md` Tier 1).
- Add a reference-manager adapter beyond BibTeX/Zotero (e.g. a Mendeley REST API
  module — see the note in `docs/integrations.md`).
- Improve error messages in `scripts/setup/*.py` for a failure mode you hit yourself.

## Pull requests

- Keep PRs scoped to one change. Update `CHANGELOG.md` under an `[Unreleased]` (or the
  next version) heading if the change is user-visible.
- Fill in the PR template checklist — it mirrors the testing steps above.
- No need to bump `package.json`'s version yourself; that happens at release time.

## Code of conduct

Be respectful and constructive. This is a small project maintained in spare time between
PhD research — response times will vary.
