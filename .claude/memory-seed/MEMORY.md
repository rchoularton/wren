# Auto-memory Index

Auto-loaded at session start. One line per entry, ≤200 lines, each pointing to a fact file in this directory. Content lives in the fact files, not here. Paper / project state belongs in `papers/{id}/STATUS.md`; behavior rules live in `.claude/rules/` (auto-loaded).

## User profile
- **Name:** (set during setup)
- **Field:** (set during setup)

## User preferences
- _(durable preferences as one-liners pointing to `user_*.md` / `feedback_*.md`)_

## Active feedback (cross-cutting; not yet promoted to rules)
- _(captured by `/retro`; promote to a rule when a correction recurs)_

## Learnings (newest first)
- _(added by `/retro`; keep to the 5 most recent index lines)_
