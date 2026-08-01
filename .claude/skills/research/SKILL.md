---
name: research
description: Access and navigate your research workspaces - papers, notes, and the corpus memory
user-invocable: true
---

# Research

An entry point to your research workspaces. Use this to orient at the start of a session.

## What to show

1. **Active paper** — read `.current_paper` and that paper's `STATUS.md`. State where it stands.
2. **Portfolio** — `npm run paper:status` for the full list.
3. **Recent thinking** — the newest entry in the active paper's `NOTES.md`.
4. **Corpus memory** (if enabled) — point at `research_memory/MEMORY.md` and offer `/research-memory recall <topic>` for cross-paper queries.
5. **Cross-session context** — recent `learning_*.md` in the auto-memory dir (the SessionStart hook already surfaced these).

Then ask what the user wants to work on. Keep it to a short orientation, not a data dump.
