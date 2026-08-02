---
name: methods-audit
description: Audit a paper's analysis scripts for exploration artifacts, stale values, and reproducibility gaps before you freeze
user-invocable: true
argument-hint: "<paper-id> [--fix]"
---

# Methods Audit

Walk a paper's analysis scripts looking for exploration-phase artifacts that could contaminate
results. Run it during methods refinement and again as a QC pass before the gold-standard
freeze (Phase 7) — catching these early is cheaper than a post-freeze rebuild.

## Usage

```
/methods-audit my-paper           # audit
/methods-audit my-paper --fix     # audit and propose fixes (one at a time)
```

## What to do

1. **Find the scripts.** Read `papers/{id}/STATUS.md`, `METHODS_LOG.md`, and `config.json`,
   then locate the analysis scripts this paper depends on — wherever the project keeps them
   (e.g. `scripts/`, `papers/{id}/`). Sketch which script feeds which, so you audit producers
   before consumers. If the project tags scripts by maturity, audit the canonical/maturing
   ones fully and only sanity-check the ones marked exploratory.

2. **Scan each script for:**
   - **Hardcoded exploration values** — magic numbers with no named constant, thresholds or
     date ranges or case lists that differ from the paper's config/scope.
   - **Stale intermediates** — outputs generated but never consumed, or cached results older
     than the inputs that should regenerate them.
   - **Leftover markers** — `TODO` / `FIXME` / `HACK` / `TEMP`, commented-out alternative
     implementations, dead branches.
   - **Reproducibility gaps** — `random`/`np.random` without a seed, OS-dependent file
     ordering, hardcoded absolute paths.
   - **Inconsistent parameters** — a window, aggregation, or column name that should match
     across scripts but doesn't.
   - **Statistical gaps** — missing multiple-comparison correction, sample sizes not reported
     with p-values, effect sizes or confidence intervals missing for key estimates.

3. **Cross-check `METHODS_LOG.md`.** Flag parameters/thresholds in the code that aren't
   documented there, and log entries that no longer match the code.

4. **Report** — a summary table (category × count × severity 🔴/⚠️/ℹ️) then detailed findings
   ordered by severity, each with the file:line and a one-line fix. Offer to save to
   `papers/{id}/reviews/methods_audit_v{N}.md`.

## `--fix` mode

For each issue: show the current code, the proposed change, and why — then **wait for approval
before editing**. Never batch fixes.

## When done

Note whether the paper is clear for the next phase (QC / gold-standard freeze), and ask
whether to record the findings in `NOTES.md`.
