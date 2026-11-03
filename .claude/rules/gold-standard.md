# Gold Standard — Meaning and Protocol

"Gold standard" means two things. Both are binding.

## 1. Highest-quality academic research

Follow research protocols. Do not take shortcuts. Do not make assumptions. Specifics are in `rigor.md` (esp. rule 5) and `no-unapproved-tasks.md`.

## 2. The versioned freeze protocol

Analysis is **frozen**, then **tested**, then **reviewed**. Freeze mechanics are owned by `/gold-standard` (`.claude/skills/gold-standard/SKILL.md`), which is authoritative. This rule governs the days *between* freezes. Tags are `{id}-gold-v{n}`, the immutable reference for that freeze.

### Frozen means immutable

A frozen artifact is never edited, corrected, or patched. Not for a typo, not for a "small" fix, not to keep a cascade cheap. If a frozen file is wrong, the answer is the next version, never an edit.

### A change means a new version

When the user decides to change something, cut version n+1 as a deliberate, complete rebuild. Do not tinker around the edges, and do not offer carry-forward, subset, or "faster" partial-rebuild options. Versions are integers only. A decimal version (`v3.1`) is a patch and the warning sign.

### Versions are documented

Every new version records what changed and why, in its `FREEZE_NOTES.md` and in `papers/{id}/METHODS_LOG.md`. A version whose rationale is not written down is not finished.

### Superseded freezes are archived, never deleted

A superseded freeze is archived in place per `outputs.md` (the `_archived_<YYYY-MM-DD>` suffix).

**How to apply:** before touching anything under a frozen tag, check whether it is frozen. If it is, the change goes into version n+1, with the rationale written into the methods log in the same step.

**Why:** edits to a frozen artifact make a citation point at something unchecked.

Background and examples: docs/rules-history.md.
