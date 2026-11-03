---
paths:
  - outputs/**
  - papers/**
  - scripts/**
description: Output & file-management conventions. Loads when working in outputs/, papers/, or scripts/.
---

# Output & File Management Rules

## 1. Never create `*_v2/` directories

Do not create a new directory alongside an original (e.g. `figures_v2/`, `analysis_v2/`). Instead:

- Archive the old directory (see §5) and reuse the original name for the new version
- If temporary parallel comparison is genuinely needed, use a **dated suffix**: `figures_20260318/`

**Why:** organic version growth produces duplicated datasets and version-ambiguous directories.

## 2. Register new output directories in MANIFEST.md

Before creating any new directory under `outputs/`, check `outputs/MANIFEST.md` first — reuse an existing directory if one fits. If you must create a new one, add it to MANIFEST.md in the same commit. Name new directories after the analysis script (snake_case).

## 3. Check CANONICAL_PATHS.md before loading shared datasets

`outputs/CANONICAL_PATHS.md` lists the canonical path for every shared dataset. Check it before loading — avoid duplicate copies and make sure you're hitting the correct version.

## 4. Processing logs go in `outputs/_logs/`

Not alongside data files.

## 5. Archive stale directories promptly

When a file or directory goes stale, rename it in place with the suffix `_archived_<YYYY-MM-DD>` (e.g. `figures_archived_2026-11-02/`) and note it in MANIFEST.md. `outputs/ARCHIVED_<reason>/` is reserved for periodic sweeps of whole directories. Check for active readers before archiving (grep `scripts/`, `papers/*/code/`, `.claude/`, `package.json`). Never delete.

## 6. Paper-specific outputs live in the paper folder

- **Figures** (publication) → `papers/{paper_id}/figures/` (PNG + PDF)
- **Key summary CSVs/JSONs** → `papers/{paper_id}/outputs/` if paper-specific
- **Analysis scripts** → stay centralized in `scripts/`
- **Central `outputs/`** → source of truth for raw pipeline data; paper folders get the curated, paper-ready versions

Background and examples: docs/rules-history.md.
