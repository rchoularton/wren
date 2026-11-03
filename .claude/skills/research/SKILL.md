---
name: research
description: Access and navigate your research workspaces - papers, notes, and the corpus memory
user-invocable: true
---

# Research

The session entry point. The orientation is a script, not a recollection.

## 1. Orient

Run `npm run status` and print its output **verbatim**. Never summarise it, reorder it, or fill gaps from memory: the report comes from the script (see `.claude/rules/always-run-the-check.md`). If the script exits non-zero, show its message and stop.

## 2. Offer the groups

- **Papers** — `/paper` (resume, switch, start a new paper)
- **Library** — `/zotero-audit`, `/lit-digest`, `/literature-scan`
- **Memory** — `/research-memory`

Do not add next steps of your own; what is pending is what the report shows from each `STATUS.md`.

## 3. Ask one question

"What do you want to work on?" Then stop and wait.
