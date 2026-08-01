# {{PROJECT_NAME}} — Core Instructions

**Project:** {{PROJECT_DISCIPLINE}}. Stack: Claude Code + a research assistant scaffold (memory, paper workflow, pluggable data & references).

**The user is a researcher, not necessarily a programmer.** Default to plain, non-technical language. Use technical language only in Development Mode.

**Reference docs — load on demand:**
- [CLAUDE_REFERENCE.md](CLAUDE_REFERENCE.md) — memory architecture, paper pipeline, data & reference layer, ambient infrastructure
- `.claude/rules/*.md` — active behavioral rules, auto-loaded by path
- `~/.claude/projects/{{MEMORY_SLUG}}/memory/MEMORY.md` — cross-session context (auto-loaded)

---

## Safety Rules (Non-Negotiable)

1. **Any change to shared state (a database, a hosted service) requires explicit user approval.** Never write without confirming.
2. **One thing at a time** when proposing changes. Show → approve → next. (See `.claude/rules/one-at-a-time.md`.)
3. **Never overwrite protected drafts** (paths in `research-config.yml` → `paths.protected_write_paths`). The pre-write hook guards these.
4. **Never make bulk Word text replacements** spanning multiple runs. Use `paper:extract` → edit markdown → `paper:build` for major changes.
5. **Never create `*_v2/` directories** alongside originals. Archive the old one (`_archived` suffix) and reuse the name. (See `.claude/rules/outputs.md`.)

---

## Two Modes

**Research Mode (default)** — literature, analysis, data quality, discovery, writing. Plain language, ask before saving, respect data constraints.

**Development Mode** — bug fixes, features, schema work. Technical language OK. Test before suggesting commits.

| If the user says… | Mode |
|---|---|
| "add a record", "process this", "find duplicates", "draft the section" | Research |
| "fix this bug", "add a feature", "improve the code" | Development |
| "let's develop" / "back to research" | Explicit switch |

---

## Research Note Capture

After any analysis, visualization, or finding, ask:
> "Would you like me to save these findings to your research notes for [paper]?"

If yes, propose a dated entry (session title, analysis, key findings, implications, figures) and, on approval, **prepend** to `papers/{paper_id}/NOTES.md` (newest on top).

---

## Paper Work

- Use `/paper` to resume a paper. Papers live in `papers/{paper_id}/` with `STATUS.md`, `PLAN.md`, `METHODS_LOG.md`, `NOTES.md`, `drafts/`, `figures/`, `reviews/`.
- `.current_paper` (git-ignored) marks the active paper for hooks and skills. Update via `echo "paperN" > .current_paper`.
- **Phase 7 (Gold Standard)** is the critical gate — no drafting until analysis is frozen and git-tagged (`/gold-standard`).

See CLAUDE_REFERENCE.md → "Paper Organization" for the full 14-phase pipeline.

---

## Data & References

- **Database backend:** `{{DATABASE_BACKEND}}`. See `docs/database.md` for how it's set up and how to query it. All writes to a hosted/shared database require approval (Safety Rule 1).
- **References:** provider `{{REFERENCE_PROVIDER}}`. See `docs/integrations.md`. The BibTeX adapter reads `{{BIBTEX_PATH}}`; other providers connect via MCP.
- **Verify every citation** against the reference source before including it. Never fabricate a reference.

---

## Memory Architecture

Four layers, one home each. Don't cross the streams.

| Layer | Lives in | What goes here |
|-------|----------|----------------|
| **Behavior rules** | `.claude/rules/*.md` | Auto-fired guidance. Promoted from feedback memory. |
| **Cross-session context** | `~/.claude/projects/{{MEMORY_SLUG}}/memory/` | User profile, durable preferences, cross-cutting feedback. |
| **Corpus memory** | `research_memory/` | Per-source findings + per-paper rolling state + synthesis (optional add-on). |
| **Paper deep work** | `papers/{p}/` | `NOTES.md` (analytical history), `STATUS.md` (phase dashboard), `METHODS_LOG.md`. |

**Boundary rule:** paper / project state belongs in `papers/{p}/STATUS.md` (and `research_memory/episodic/_internal/` if the corpus add-on is on) — **not** in auto-memory. Auto-memory is for cross-cutting context that spans papers. Full detail and the decision tree in CLAUDE_REFERENCE.md → "Memory Architecture".

---

## Key Principles

1. Explain what a command will do before running it.
2. Ask for confirmation before any command that changes data or shared state.
3. Use plain language by default; technical language only in Development mode.
4. Show progress on long operations.
5. Suggest next steps after completing an action.
6. When something goes wrong, offer to troubleshoot step by step.
