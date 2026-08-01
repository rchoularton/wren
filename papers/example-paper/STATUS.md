---
paper_id: example-paper
title: "Example Working Paper — replace with your title"
journal: "Target Journal"
phase: 1
tier: 2
status: scoping
tags: [example]
aliases: ["Example Paper"]
---

# Example Paper — Status

**Target journal:** Target Journal
**Status:** Phase 1 — scoping
**Last updated:** (set when you start)

## ▶ RESUME HERE

**This is a template.** To start a real paper, duplicate this folder:

```bash
cp -r papers/example-paper papers/my-paper
echo "my-paper" > .current_paper
```

Then edit this file's frontmatter (`paper_id`, `title`, `journal`, `phase`) and delete this note.

## Phase checklist (14-phase pipeline)

- [x] 1. Scoping
- [ ] 2. Data inventory
- [ ] 3. Exploratory analysis
- [ ] 4. Methods design
- [ ] 5. Analysis build
- [ ] 6. QC review
- [ ] 7. **Gold Standard freeze (git tag)** ← no drafting before this
- [ ] 8. Drafting
- [ ] 9. Figures
- [ ] 10. Internal review
- [ ] 11. QC of draft
- [ ] 12. Submission prep
- [ ] 13. Peer-review response
- [ ] 14. Publication

## Notes

Analytical history lives in `NOTES.md` (newest on top). Methods decisions in `METHODS_LOG.md`. Forward plan in `PLAN.md`.
