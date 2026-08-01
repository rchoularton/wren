# Corpus Memory — Dashboard

This is the entry point to your **corpus memory** (Layer 3): a two-layer episodic + semantic memory over your literature and projects. Distinct from cross-session auto-memory (Layer 2) — see `CLAUDE_REFERENCE.md` → Memory Architecture.

Query it with the `/research-memory` skill (`recall`, `status`, `log`, `inspect`), or just `grep` the files.

## Layout

- `episodic/_external/_by-citekey/` — one note per literature source (findings, themes, links to your papers)
- `episodic/_internal/{papers,country,special}/` — rolling state per research artifact (the source of truth for a paper's themes and linked sources)
- `semantic/{themes,questions,gaps,contradictions}/` — distilled cross-corpus synthesis
- `reflections/REFLECTIONS.md` — periodic synthesis, newest on top

## Current state

- **Papers tracked:** example-paper
- **External sources:** 0 (add via `/research-memory` or the future Zotero-ingestion module)
- **Open questions / gaps / contradictions:** see `semantic/`

_Update this dashboard as the corpus grows._
