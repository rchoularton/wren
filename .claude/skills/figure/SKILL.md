---
name: figure
description: Multi-agent figure iteration - Designer improvements, Critic scoring - to reach publication quality
user-invocable: true
argument-hint: "<paper-id> [--figure N] [--all] [--max-iterations N] [--score-only]"
---

# Figure

Iterates a figure toward publication quality using a Designer → Critic loop. The two
personas run as **isolated sub-agents** (`.claude/agents/figure-designer.md`,
`.claude/agents/scientific-graphics-reviewer.md`), invoked via the Agent tool. Context
isolation matters here too: the Critic scores what's actually on disk, not the
Designer's running commentary about it.

A natural fit whenever figures need to go from "readable" to "ready for your target
journal" — typically once the underlying analysis is frozen (`/gold-standard`) and
you're moving into drafting or submission prep.

## Usage

```
/figure my-paper --figure 2          # work on one figure, checkpointed
/figure my-paper --all               # iterate every figure
/figure my-paper --score-only        # audit current figures, no changes
```

## Workflow (orchestration)

### Step 0 — Scope

1. Read `papers/{id}/config.json` for the target journal.
2. Glob `papers/{id}/figures/*` for figure-generation scripts and their current
   output images (whatever tool the project uses — Python/Matplotlib, R, etc.).
3. For each figure, identify its **type** — conceptual framework, time series, map,
   multi-panel, or bar/dot chart. The Critic's rubric has type-specific overrides, so
   getting this right matters.

**CHECKPOINT (interactive mode)** — present the inventory and ask which figure(s) to
work on, unless `--figure N` or `--all` was already given:

```
Paper: {id} → {journal}
Figures found: {N}
  1. figure1_xxx.py → figure1_xxx.png [TYPE: time series]
  2. figure2_xxx.py → figure2_xxx.png [TYPE: map]

Which figure(s) to work on? [1/2/all]
```

### Step 1 — Designer

Invoke the **`figure-designer`** sub-agent via the Agent tool with a self-contained
brief: `paper_id`, the target journal (and any known dimension/DPI/font conventions
for it), the exact script and image paths, the figure type, and — on iteration 2+ —
the most recent Critic scorecard with its priority fixes. Wait for it to finish;
confirm the new image exists on disk.

**CHECKPOINT (interactive mode):** show the Designer's bullet list of changes and the
regenerated figure. Ask "Proceed to Critic scoring? [y/n]".

### Step 2 — Critic

Invoke the **`scientific-graphics-reviewer`** sub-agent via the Agent tool with the
figure image, script, journal target, and figure type. It runs its mandatory
pre-scoring narrative and 8-dimension rubric — see `scientific-graphics-reviewer.md`
for the full scoring definitions and hard gates — and returns a structured scorecard
with a weighted percentage and priority fixes.

Pass threshold: **≥ 95%**, with two hard gates that fail the figure regardless of the
aggregate score — Clarity of Message ≥ 4, Technical Compliance = 5.

### Step 3 — Decide

- **Score ≥ 95% and both gates pass:** present the scorecard and ask whether to
  accept the figure as publication-ready.
- **Below 95%, iterations remaining (`--max-iterations`, default 3):** hand the top
  2–3 priority fixes from the scorecard back to Step 1 and loop.
- **Below 95%, max iterations reached:** present the remaining issues and ask
  whether to accept at current quality, continue for more iterations, or hand off
  for manual editing.

### `--all` (multiple figures)

Run Step 0 once for the whole paper and get the figure-set approved. Then run the
Step 1 → Step 2 → Step 3 loop per figure. Figures are independent: if the user hasn't
asked to review each iteration, launch each figure's Designer/Critic loop as a
separate Agent tool call in the same message so they run in parallel, then present a
single summary table at the end. If the user wants to review changes as they happen,
run figures one at a time using the checkpointed flow instead.

Before launching anything, verify every script and image path actually resolves on
disk (`ls`) — never hand a sub-agent a guessed or templated path.

### `--score-only`

Skip Step 1 entirely. Run Step 0, then Step 2 for every selected figure without
making any changes, and present a summary audit table:

```
| Figure | Type | Score | Gates | Status |
|--------|------|-------|-------|--------|
| Figure 1 | Framework | 62% | ✅❌ | Needs design work |
| Figure 2 | Time series | 92% | ✅✅ | Near-ready |
```

## Output

No fixed output directory — the Designer edits scripts and regenerates images in
place under `papers/{id}/figures/`. If your project keeps per-paper research notes,
offer to save a dated entry to `papers/{id}/NOTES.md` after a completed session.

## Why two sub-agents, not one loop

- **Context isolation** — the Critic scores the artifact on disk, not the Designer's
  reasoning about it. That separation is what keeps the score honest.
- **Reusability** — `scientific-graphics-reviewer` can be invoked directly for a
  score-only audit without going through the full Designer loop.
- **Different tiers** — design/production work runs on a faster model; scoring is a
  QC gate and runs on the stronger one (see `.claude/rules/token-budget.md` if your
  project has it, or the model field on each agent).

## Key principles

1. **Design quality over technical compliance** — a figure that hits every DPI and
   font spec but has flat visual hierarchy is not publication-ready. See the
   Critic's calibration anchor in `scientific-graphics-reviewer.md`.
2. **Preserve research intent** — the Designer improves presentation; it does not
   change what the figure communicates.
3. **One figure at a time in interactive mode** — show progress incrementally unless
   `--all` was explicitly requested (`.claude/rules/one-at-a-time.md`).
4. **Always show changes before overwriting an image** — get approval first.
5. **Never inflate scores** — a technically compliant but poorly designed figure
   scores 50–65%, not 90%+.
