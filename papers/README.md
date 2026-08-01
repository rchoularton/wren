# Papers

Each paper is a self-contained folder following one template. To start a new paper, duplicate the example:

```bash
cp -r papers/example-paper papers/my-paper
echo "my-paper" > .current_paper      # marks it active for hooks + skills
```

Then edit `papers/my-paper/STATUS.md` frontmatter.

## The per-paper template

| File / dir | What it holds |
|---|---|
| `STATUS.md` | Phase/status dashboard (YAML frontmatter) + a "▶ RESUME HERE" pointer |
| `PLAN.md` | Forward-looking task plan |
| `METHODS_LOG.md` | Methods decisions and pre-registration |
| `NOTES.md` | Long-form analytical history, newest on top |
| `config.json` | Title, journal style, version, optional external draft-sync path |
| `drafts/` | Markdown and Word drafts (build with `npm run paper:build <id>`) |
| `figures/` | Publication figures (PNG + PDF) |
| `outputs/` | Paper-specific summary CSVs/JSONs |
| `reviews/` | Reviewer comments and response documents |
| `gold_standard/` | Frozen, git-tagged canonical analysis (Phase 7) |

## The 14-phase pipeline

See `CLAUDE_REFERENCE.md` → "Paper Organization". Phase 7 (Gold Standard freeze) is the gate: no drafting until the analysis is frozen and git-tagged.

## Building drafts

```bash
npm run paper:status              # overview of all papers
npm run paper:status my-paper     # sync status for one paper
npm run paper:build my-paper      # Markdown → Word (.docx)
npm run paper:extract my-paper    # Word → Markdown (round-trip)
```
