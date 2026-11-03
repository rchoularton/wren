# {{PROJECT_NAME}} — Core Instructions

**Project:** {{PROJECT_DISCIPLINE}}. Stack: Claude Code + a research assistant scaffold.

**The user is a researcher, not necessarily a programmer.** Default to plain, non-technical language; technical language only in Development Mode.

**Reference docs — load on demand:**
- [CLAUDE_REFERENCE.md](CLAUDE_REFERENCE.md) — memory, paper pipeline, data & reference layer
- `.claude/rules/*.md` and `~/.claude/projects/{{MEMORY_SLUG}}/memory/MEMORY.md` — auto-loaded

---

## Safety Rules (Non-Negotiable)

1. **Any change to shared state (a database, a hosted service) requires explicit user approval.** Never write without confirming.
2. **One thing at a time** when proposing changes (`.claude/rules/one-at-a-time.md`).
3. **Never overwrite protected drafts** (paths in `research-config.yml` → `paths.protected_write_paths`). The pre-write hook guards these.
4. **Never make bulk Word text replacements** spanning multiple runs. Use `paper:extract` → edit markdown → `paper:build` for major changes.
5. **Never create `*_v2/` directories** alongside originals (`.claude/rules/outputs.md`).

---

## Two Modes

**Research Mode (default)** — literature, analysis, data quality, discovery, writing. Ask before saving, respect data constraints.

**Development Mode** — bug fixes, features, schema work. Test before suggesting commits.

Switch explicitly with "let's develop" / "back to research". "add a record", "process this", "find duplicates", "draft the section" are Research; "fix this bug", "add a feature", "improve the code" are Development.

---

## Research Note Capture

After any analysis, visualization, or finding, ask:
> "Would you like me to save these findings to your research notes for [paper]?"

If yes, propose a dated entry (session title, analysis, key findings, implications, figures) and, on approval, **prepend** to `papers/{paper_id}/NOTES.md` (newest on top).

---

## Paper Work

- Use `/paper` to resume a paper. Papers live in `papers/{paper_id}/` (`STATUS.md`, `PLAN.md`, `METHODS_LOG.md`, `NOTES.md`, `drafts/`, `figures/`, `reviews/`).
- `.current_paper` (git-ignored) marks the active paper for hooks and skills. Update via `echo "paperN" > .current_paper`.
- **Phase 7 (Gold Standard)** is the critical gate — no drafting until analysis is frozen and git-tagged (`/gold-standard`).

See CLAUDE_REFERENCE.md → "Paper Organization" for the full 14-phase pipeline.

---

## Data & References

- **Database backend:** `{{DATABASE_BACKEND}}`. See `docs/database.md` for how it's set up and how to query it.
- **References:** provider `{{REFERENCE_PROVIDER}}`. See `docs/integrations.md`. The BibTeX adapter reads `{{BIBTEX_PATH}}`; other providers connect via MCP.
- **Verify every citation** against the reference source (`.claude/rules/always-run-the-check.md`). Never fabricate a reference.

---

## Memory Architecture

Four layers, one home each: behavior rules (`.claude/rules/*.md`), cross-session context (`~/.claude/projects/{{MEMORY_SLUG}}/memory/`), corpus memory (`research_memory/`, optional add-on), paper deep work (`papers/{p}/`).

**Boundary rule:** paper / project state belongs in `papers/{p}/STATUS.md` (and `research_memory/episodic/_internal/` if the corpus add-on is on) — **not** in auto-memory, which is for cross-cutting context that spans papers. Decision tree: CLAUDE_REFERENCE.md → "Memory Architecture".

---

## Key Principles

1. Explain what a command will do before running it; ask for confirmation before any that changes data or shared state.
2. Show progress on long operations; suggest next steps after completing an action.
3. When something goes wrong, offer to troubleshoot step by step.
