---
name: gold-standard
description: Freeze an analysis as canonical - verify outputs, git-tag, and archive as the paper's gold standard (Phase 7 gate)
user-invocable: true
argument-hint: [paper-id]
---

# Gold Standard Freeze

Phase 7 — the gate between analysis and drafting. This makes a paper's analysis **canonical**: verified, reproducible, git-tagged, and archived. After this, results may be cited in prose; before it, everything is exploration.

## Steps

1. **Re-run the pipeline clean.** Run the paper's analysis end-to-end from raw inputs, not from cached intermediates. Confirm it reproduces.
2. **Verify the headline numbers.** Pull every number that will appear in the paper from the freshly produced outputs. Record them. (This is the canonical set the `/draft` skill must quote.)
3. **Archive the outputs.** Copy the verified outputs into `papers/{id}/gold_standard/` with a short `FREEZE_NOTES.md`: date, input data versions, script commit, and the headline numbers.
4. **Git-tag it.** Commit the frozen state and tag it, e.g. `git tag {id}-gold-v1`. The tag is the immutable reference.
5. **Update STATUS.md.** Set `phase: 7` and `status: gold_standard_v1`. Tick the Phase 7 box.

## Rules

- Do not freeze if the pipeline doesn't reproduce cleanly — fix that first.
- Once frozen, changing an analysis means a **new** freeze (`-gold-v2`), not editing the old one.
- Only frozen results are canonical (`.claude/rules/rigor.md` rule 3). Everything else must be labelled exploration when discussed.
