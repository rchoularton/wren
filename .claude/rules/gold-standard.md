---
description: Gold-standard protocol, always on. Defines what gold standard means and the freeze and versioning discipline that governs work between freezes.
---

# Gold Standard — Meaning and Protocol

"Gold standard" means two things. Both are binding.

## 1. Highest-quality academic research

Follow research protocols. Do not take shortcuts. Do not make assumptions. The specific behaviours are in `rigor.md` (esp. rule 5, no silent shortcuts) and `no-unapproved-tasks.md`.

## 2. The versioned freeze protocol

Analysis is **frozen**, then **tested**, then **reviewed**.

The mechanics of executing a freeze are owned by `/gold-standard` (`.claude/skills/gold-standard/SKILL.md`). That skill is authoritative. This rule governs the days *between* freezes, which the skill does not reach.

Tags follow the convention `{id}-gold-v{n}`, for example `{id}-gold-v1`. The tag is the immutable reference for that freeze.

### Frozen means immutable

A frozen artifact is never edited, corrected, or patched. Not for a typo, not for a "small" fix, not to keep a cascade cheap. If a frozen file is wrong, the answer is the next version, never an edit.

### A change means a new version

When the user decides to change something, cut version n+1 as a deliberate, complete rebuild. Do not tinker around the edges, and do not offer carry-forward, subset, or "faster" partial-rebuild options. Versions are integers only.

**Decimal versions are the warning sign.** A `v3.1` or `v3.2` is by construction a patch to v3 rather than a new version, and it is exactly the pattern this rule exists to stop.
### Versions are documented

Every new version records what changed and why, in its `FREEZE_NOTES.md` and in `papers/{id}/METHODS_LOG.md`. A version whose rationale is not written down is not finished.

### Superseded freezes are archived, never deleted

Every freeze is kept. A superseded freeze is archived in place per `outputs.md` (the `_archived_<YYYY-MM-DD>` suffix), so live and historical artifacts are distinguishable at a glance.

## Why

A result is only as reproducible as the version it cites. Edits to a frozen artifact make the citation point at something other than what was checked, and decimal patches hide that change. Integer versions with written rationales keep every result traceable to the exact state that produced it.

## How to apply

Before touching anything under a frozen tag, check whether it is frozen. If it is, the change goes into version n+1. Write the rationale into the methods log in the same step.
