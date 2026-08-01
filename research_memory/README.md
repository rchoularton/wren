# Corpus Memory (`research_memory/`)

An optional add-on: a **two-layer memory over your research corpus** — the literature you read and the projects you run. It's Layer 3 of the memory architecture (see `CLAUDE_REFERENCE.md`). Enable it with `tiers.research_memory: true` in `research-config.yml`.

It's plain Markdown with YAML frontmatter, queryable by `grep` and by the `/research-memory` skill. No database, no server.

## The two layers

**Episodic** — atomic, dated records:
- `episodic/_external/_by-citekey/{citekey}.md` — one note per literature source: what it found, which of your papers it bears on, confidence, themes.
- `episodic/_internal/{papers,country,special}/{id}.md` — rolling state per research artifact. The **source of truth** for a paper's themes, linked sources, and status.

**Semantic** — distilled synthesis across the episodic layer:
- `semantic/themes/` — recurring themes
- `semantic/questions/` — OPEN and ANSWERED questions (stable IDs)
- `semantic/gaps/` — where the literature/analysis is thin
- `semantic/contradictions/` — where sources disagree (stable IDs)
- `reflections/REFLECTIONS.md` — periodic synthesis, newest on top

## How to populate it (v1, zero-dependency)

1. **Manually** — write a note file directly, following the frontmatter shape in `episodic/_internal/papers/example-paper.md`.
2. **Via the skill** — `/research-memory log <artifact> "<note>"` appends a note; `/research-memory recall <topic>` greps across the layers; `/research-memory status` summarizes.
3. **Via `/retro`** — research-domain learnings can be filed here instead of auto-memory (keeps auto-memory lean).

## The automated Zotero-ingestion module (future / advanced)

The system this kit was extracted from runs a **nightly headless job** that reads new items from a Zotero library (tagged `memory-pending`), extracts a structured note per source with an LLM, and files it under `episodic/_external/`, then a weekly job distills the semantic layer. That engine is **Zotero-coupled** and is intentionally *not* shipped in v1 — it needs the `zotero` reference provider and a batch/tagging workflow.

If you want it, the pattern is documented and the `config.json → automated_ingestion` block reserves the settings. Building it is a good contribution: a `scripts/research_memory/` engine that (a) pulls tagged items from your reference provider, (b) extracts a note per source, (c) writes the episodic file + updates the index, (d) runs a periodic reflection to update the semantic layer. Wire it as a scheduled job (see the scheduled-jobs module) once built.
