---
name: draft
description: Turn frozen analysis outputs into paper sections - journal mode or working-paper mode
user-invocable: true
argument-hint: [paper-id] [section]
---

# Draft

Turn analysis into prose. **Precondition:** the analysis must be frozen (Phase 7, `/gold-standard`). Do not draft on un-frozen numbers — if the paper isn't at Phase 7, say so and stop.

## Before drafting

1. Confirm the paper's phase in `papers/{id}/STATUS.md` is ≥ 7.
2. Read the frozen outputs in `papers/{id}/gold_standard/` and the methods trail in `METHODS_LOG.md`.
3. Read the latest `NOTES.md` entries for the analytical narrative.
4. Pull the target journal's expectations from `config.json` / `research-config.yml`.

## Drafting rules

- **Every number** comes from the frozen outputs — quote the source, never estimate.
- **Every citation** is verified against your reference source (see `docs/integrations.md`); never fabricate one.
- **Human prose, not AI-tells:** no em-dashes, no formulaic connectives ("Moreover", "It is important to note"), varied sentence rhythm. (See `.claude/rules/reviewer-response-prose.md` for the anti-AI standard — it applies to all drafted text.)
- Present one section at a time; wait for feedback before the next (`.claude/rules/one-at-a-time.md`).

## Output

Write drafts to `papers/{id}/drafts/` as Markdown. Build to Word with `npm run paper:build {id}` when the user is ready.
