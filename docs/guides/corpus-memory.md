# Corpus memory

Corpus memory (`research_memory/`) is an **optional add-on** — a two-layer memory over your research corpus: the literature you read and the projects you run. It's Layer 3 of the [four-layer memory model](../concepts.md#the-four-layer-memory-model). Enable it with `tiers.research_memory: true` in `research-config.yml` (it defaults to `true` in `research-config.example.yml`).

It's plain Markdown with YAML frontmatter, queryable by `grep` and by the `/research-memory` skill. No database, no server.

## The two layers

**Episodic** — atomic, dated records:

- `episodic/_external/_by-citekey/{citekey}.md` — one note per literature source: what it found, which of your papers it bears on, confidence, themes.
- `episodic/_internal/{papers,country,special}/{id}.md` — rolling state per research artifact. This is the **source of truth** for a paper's themes, linked sources, and status.

**Semantic** — distilled synthesis across the episodic layer:

- `semantic/themes/` — recurring themes
- `semantic/questions/` — OPEN and ANSWERED questions (stable IDs)
- `semantic/gaps/` — where the literature/analysis is thin
- `semantic/contradictions/` — where sources disagree (stable IDs)
- `reflections/REFLECTIONS.md` — periodic synthesis, newest on top

## How to populate it (v1)

!!! note "Set expectations honestly"
    In v1, populating corpus memory is **largely manual**. There is no automated ingestion pipeline shipped yet — the three paths below are what you actually do today.

1. **Manually** — write a note file directly, following the frontmatter shape in `episodic/_internal/papers/example-paper.md`.
2. **Via the skill** — `/research-memory log <artifact> "<note>"` appends a note; `/research-memory recall <topic>` greps across the layers; `/research-memory status` summarizes.
3. **Via `/retro`** — research-domain learnings can be filed here instead of auto-memory, keeping auto-memory lean.

Two npm scripts support the tier itself rather than populating it:

```bash
npm run memory:bootstrap   # idempotent scaffolder/repair for the memory tree
npm run memory:audit       # offline health/completeness check (JSON log + severity findings)
```

## The automated Zotero-ingestion module (future / advanced)

The system this kit was extracted from runs a **nightly headless job** that reads new items from a Zotero library (tagged `memory-pending`), extracts a structured note per source with an LLM, files it under `episodic/_external/`, then a weekly job distills the semantic layer. That engine is **Zotero-coupled** and is intentionally **not shipped in v1** — it needs the `zotero` reference provider (see [References & integrations](references.md)) and a batch/tagging workflow.

If you want it, the pattern is documented and `config.json → automated_ingestion` reserves the settings. Building it is a good contribution: a `scripts/research_memory/` engine that:

1. pulls tagged items from your reference provider,
2. extracts a note per source,
3. writes the episodic file and updates the index,
4. runs a periodic reflection to update the semantic layer,

wired as a scheduled job once built. See [Contributing](../contributing.md).
