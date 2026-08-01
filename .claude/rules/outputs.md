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

- Archive the old directory: rename with an `_archived` suffix (e.g. `figures_archived/`)
- Reuse the original name for the new version
- If temporary parallel comparison is genuinely needed, use a **dated suffix**: `figures_20260318/`

**Why:** Organic version growth produces duplicated datasets and version-ambiguous directories that are painful to clean up later.

## 2. Register new output directories in MANIFEST.md

Before creating any new directory under `outputs/`, check `outputs/MANIFEST.md` first — reuse an existing directory if one fits. If you must create a new one, add it to MANIFEST.md in the same commit. Name new directories after the analysis script (snake_case).

## 3. Check CANONICAL_PATHS.md before loading shared datasets

`outputs/CANONICAL_PATHS.md` lists the canonical path for every shared dataset. Check it before loading — avoid duplicate copies and make sure you're hitting the correct version.

## 4. Processing logs go in `outputs/_logs/`

Not alongside data files.

## 5. Archive stale directories promptly

When a directory goes stale, move it to `outputs/ARCHIVED_<reason>/` and note it in MANIFEST.md.

## 6. Paper-specific outputs live in the paper folder

For publication figures and key summary outputs tied to a specific paper:

- **Figures** → `papers/{paper_id}/figures/` (PNG + PDF)
- **Key summary CSVs/JSONs** → `papers/{paper_id}/outputs/` if paper-specific
- **Analysis scripts** → stay centralized in `scripts/`
- **Central `outputs/`** → remains the source of truth for raw pipeline data

Central outputs is for raw data; paper folders get the curated, paper-ready versions.
