# Auto-memory Index

Auto-loaded at session start. Keep it ≤200 lines: one line per entry, pointing to a fact file in this directory. Content lives in the fact files, not here.

**For paper / project state** → `papers/{id}/STATUS.md` (and `research_memory/` if the corpus add-on is on).
**For active behavior rules** → `.claude/rules/` (auto-loaded by path).

## User profile

- **Name:** (set during setup)
- **Field:** (set during setup)

## User preferences

- _(add durable preferences here as one-liners pointing to `user_*.md` / `feedback_*.md` files)_

## Behavior rules (active, in `.claude/rules/`)

- `rigor.md` — read-first, no embellishment, only frozen pipelines are canonical, no stale exploration, no silent shortcuts
- `one-at-a-time.md` — present items ONE per message; stop and wait
- `no-unapproved-tasks.md` — never add tasks/scope without explicit approval
- `tooling.md` — terminal-first; editor-visibility workaround
- `outputs.md` — output/file-management conventions (path-scoped)
- `reviewer-response-prose.md` — reviewer-response format + anti-AI prose (path-scoped)

## Active feedback (cross-cutting; not yet promoted to rules)

- _(captured by `/retro`; promote to a rule when a correction recurs)_

## Learnings (newest first)

- _(added by `/retro`; keep to the 5 most recent index lines)_
