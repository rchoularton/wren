# Research Rigor Rules

Follow these without being asked.

## 1. Never assume — read existing work first

When a plan, script, or document already exists: **read it fully before proposing anything**. When the user says "let's run X", open X and review it with them first — don't start building a separate version. Ask clarifying questions rather than guessing. Don't recreate work the user already spent time on.

## 2. Never embellish figure descriptions

Only state what you can verify from the data. Do NOT describe anything in a figure that isn't unambiguously visible or confirmed by querying the underlying data.

- "Bars in the bottom lane" ✓ — "bars indicating severe crisis" ✗ (unless confirmed)
- Never use phrases like "reaching close to -3" or "dramatic anomaly" unless you queried the value
- When uncertain about a value, query before stating it; err on the side of saying less

## 3. Only frozen pipelines are canonical

A result is canonical **only** once its pipeline has been frozen via `/gold-standard` (verified, git-tagged, archived). Everything else — exploratory scripts, draft analyses, work-in-progress — is exploration, and often produces results that don't hold up.

- Never present results from un-frozen scripts as validated findings
- When discussing exploration outputs, say so explicitly
- A script becomes canonical only when the user runs `/gold-standard` on it

## 4. Don't build on stale exploration

When designing a new analysis stage, do NOT reuse outputs from earlier exploration without verifying they match the current framework's resolution, coverage, and pipeline. Before reusing any output, check: **same resolution? same variable set? same universe of cases?** If not, reimplement on the correct data — reference the technique, don't inherit the data path.

## 5. Run skills and commands to their FULL defined process — no silent shortcuts

When a skill or workflow defines a multi-stage process, run **every** stage. Do not skip, abbreviate, or substitute assumptions for a stage that calls for fresh work (a search, a fetch, a checkpoint) unless the user explicitly tells you to. "Clean", "full", "proper", and "rigorous" all mean **the complete defined process at maximum rigor**.

If a stage genuinely cannot run as designed, **say so up front and run it another way** — do not quietly drop it. When reporting results, state which stages ran and which did not. Never present a headline verdict (a score, an "accept", a "verified") as if the full process backed it when part was skipped.

For `/peer-review` and `/qc-team` the `post-agent-review-gate` hook blocks a `peer-review-editor` or `qc-team-leader` verdict when a required prior-stage file for that paper and version is missing. A missing comparative analysis only warns.

For long analysis sessions, run `/rigor-check` partway through to self-audit.

**Why:** a competent-looking shortcut hides the gap, and high-consequence QC cannot tolerate fabricated observations.

Background and examples: docs/rules-history.md.
