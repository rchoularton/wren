---
name: paper
description: Paper portfolio management - check status, resume work, navigate papers, start a new paper
user-invocable: true
argument-hint: [paper-id]
---

# Paper

Manage and resume research papers. Papers live in `papers/{id}/` (see `papers/README.md`).

## No argument — portfolio overview

Run `npm run paper:status` and summarize: for each paper, its title, journal, phase, and status (from `STATUS.md` frontmatter). Point out which paper is currently active (`.current_paper`). Ask which one to resume.

## With a paper id — resume that paper

1. `echo "{id}" > .current_paper` so hooks and skills track it.
2. Read `papers/{id}/STATUS.md` — especially the "▶ RESUME HERE" pointer and the phase checklist.
3. Skim the most recent entry in `papers/{id}/NOTES.md` and any open items in `PLAN.md`.
4. Summarize where the paper stands and the obvious next step. Do **not** invent tasks — surface what's written; propose next steps as questions (see `.claude/rules/no-unapproved-tasks.md`).

## Starting a new paper

Duplicate the template and edit the frontmatter:
```bash
cp -r papers/example-paper papers/{new-id}
echo "{new-id}" > .current_paper
```
Then walk the user through setting `title`, `journal`, and `phase` in `STATUS.md`.

## Housekeeping (on request)

- Confirm `STATUS.md` frontmatter matches reality (phase, status).
- Check drafts are synced (`npm run paper:status {id}`).
- Remind the user of the Phase 7 gate: no drafting until analysis is frozen via `/gold-standard`.
