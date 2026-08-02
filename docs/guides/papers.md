# Papers & the build engine

Every paper in the kit lives at `papers/{id}/` and moves through the same [14-phase pipeline](../concepts.md#the-14-phase-paper-pipeline), gated at Phase 7 by the gold-standard freeze. This guide covers the per-paper template and the Markdown⇄Word build engine that lets you draft in Markdown and hand a real `.docx` to supervisors and journals.

## The per-paper template

Duplicate `papers/example-paper/` to start a new one:

```bash
cp -r papers/example-paper papers/my-first-paper
echo "my-first-paper" > .current_paper
```

Setting `.current_paper` matters beyond bookkeeping: the **UserPromptSubmit hook** reads it and injects that paper's status into every turn, so the assistant always knows which paper you mean without you repeating context.

Each paper folder contains:

| Path | Purpose |
|---|---|
| `STATUS.md` | Phase/status dashboard, YAML frontmatter (see below). Write trigger: phase transitions, freezes. |
| `PLAN.md` | Forward-looking task plan. Write trigger: phase planning. |
| `METHODS_LOG.md` | Methods decisions and pre-registration. Write trigger: each methods choice. |
| `NOTES.md` | Long-form analytical history, dated newest-on-top. Write trigger: after analysis. |
| `config.json` | Paper-level config. |
| `drafts/` | Markdown source the build engine reads from. |
| `figures/` | Generated figures. |
| `outputs/` | Analysis outputs specific to this paper. |
| `reviews/` | Peer-review and QC artifacts. |
| `gold_standard/` | Frozen, tagged analysis snapshots (Phase 7 output). |

`STATUS.md` frontmatter shape:

```yaml
---
paper_id: my-paper
title: "…"
journal: "Target Journal"
phase: 1
tier: 2
status: scoping
tags: [paper]
aliases: ["My Paper"]
---
```

## The Markdown⇄Word build engine

Draft in Markdown, review in Word. The engine round-trips between the two so you can write in `papers/{id}/drafts/` and produce a `.docx` for anyone who needs one — then bring their tracked-changes edits back into Markdown.

One-time setup (needs `python-docx` and `markdown`, listed in `requirements.txt` — the scaffolder doesn't install these for you):

```bash
npm run paper:setup
```

Then, for any paper:

```bash
npm run paper:status                    # portfolio-wide phase/status dashboard
npm run paper:build my-first-paper      # Markdown → .docx
npm run paper:extract my-first-paper    # .docx → Markdown (round-trip)
```

- **`paper:build`** reads the Markdown in `papers/{id}/drafts/` and produces a formatted `.docx`.
- **`paper:extract`** reads a `.docx` (for example one a co-author edited with Track Changes) back into Markdown, so edits flow back into the source of truth.
- **`paper:status`** / **`paper:list`** give a portfolio-wide view of every paper's phase and status — useful for `/paper` to orient at the start of a session.

!!! note "If a command fails with a missing-dependency error"
    `paper:build` / `paper:extract` print a clear "run `npm run paper:setup`" message instead of a Python traceback if `python-docx` or `markdown` aren't installed yet. Run `npm run paper:setup` once and retry.

## Why the freeze gate matters

Phase 7 (`/gold-standard`) is deliberately the one hard stop in the pipeline: no drafting starts until the analysis behind it is verified, git-tagged, and archived as canonical. This exists to prevent the common failure mode of writing prose around numbers that then change under you as analysis continues. Once frozen, that version of the analysis is immutable — a later correction is always a new frozen version, never an edit to the old one.
