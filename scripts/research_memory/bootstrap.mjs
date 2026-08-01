#!/usr/bin/env node
/**
 * research-memory bootstrap — idempotent scaffolder / repair.
 *
 * Creates (or repairs) the corpus-memory directory tree described by
 * `research_memory/config.json`: every episodic/semantic directory, a
 * `.gitkeep` in the ones that would otherwise be empty, the seeded index /
 * dashboard files, and a rolling-state file for each artifact listed in
 * `config.internal_artifacts`.
 *
 * Idempotent and non-destructive: existing files are never overwritten. Run it
 * on a fresh project to lay the tree down, or any time to repair a deletion.
 *
 * Usage:
 *   node scripts/research_memory/bootstrap.mjs            # scaffold / repair
 *   node scripts/research_memory/bootstrap.mjs --quiet     # summary line only
 *   node scripts/research_memory/bootstrap.mjs --force     # ignore the tier gate
 */

import fs from 'node:fs';
import path from 'node:path';
import {
  loadConfig,
  resolvePath,
  researchMemoryEnabled,
  artifactToTier,
  PROJECT_ROOT,
} from './config.mjs';

const args = process.argv.slice(2);
const QUIET = args.includes('--quiet');
const FORCE = args.includes('--force');

function log(msg) {
  if (!QUIET) console.log(msg);
}

if (!researchMemoryEnabled() && !FORCE) {
  log('research_memory tier is disabled (tiers.research_memory: false in research-config.yml).');
  log('Enable it and re-run, or pass --force. Nothing to do.');
  process.exit(0);
}

const cfg = loadConfig();
const created = [];

// --- fs helpers (all paths project-relative, as stored in config.json) ------

function ensureDir(rel) {
  const abs = resolvePath(rel);
  if (!fs.existsSync(abs)) {
    fs.mkdirSync(abs, { recursive: true });
    created.push(`dir   ${rel}`);
  }
  return abs;
}

function ensureGitkeep(rel) {
  ensureDir(rel);
  const abs = path.join(resolvePath(rel), '.gitkeep');
  if (!fs.existsSync(abs)) {
    fs.writeFileSync(abs, '');
    created.push(`file  ${path.relative(PROJECT_ROOT, abs)}`);
  }
}

function ensureFile(rel, contents) {
  const abs = resolvePath(rel);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  if (!fs.existsSync(abs)) {
    fs.writeFileSync(abs, contents);
    created.push(`file  ${rel}`);
  }
}

/** Minimal frontmatter field read (no YAML dep) — used to fill the index. */
function fmValue(filepath, field) {
  if (!fs.existsSync(filepath)) return null;
  const txt = fs.readFileSync(filepath, 'utf8');
  if (!txt.startsWith('---\n')) return null;
  const end = txt.indexOf('\n---\n', 4);
  if (end === -1) return null;
  const fm = txt.slice(4, end);
  const re = new RegExp('^' + field + '\\s*:\\s*(.*)$', 'm');
  const m = fm.match(re);
  return m ? m[1].trim() : null;
}

// --- seed templates (mirror the files the kit ships) ------------------------

const SEED = {
  externalIndex: `# External Sources Index

One line per literature source note in \`_by-citekey/\`. Newest additions at the bottom.

| Citekey | Title | Linked papers | Themes |
|---------|-------|---------------|--------|
| _(none yet)_ | | | |
`,
  themesIndex: `# Themes

Cross-corpus themes distilled from the episodic layer. One entry per theme.

_(empty — populate as patterns emerge across sources and papers)_
`,
  open: `# Open Questions

Unresolved questions raised across the corpus. Each gets a stable ID (Q-YYYY-MM-DD-NNN).

_(none yet)_
`,
  answered: `# Answered Questions

Questions from OPEN.md that have been resolved, with the answer and its source.

_(none yet)_
`,
  gaps: `# Gaps

Where the literature or your own analysis is thin. Drives what to read or run next.

_(none yet)_
`,
  contradictions: `# Contradictions

Where sources or analyses disagree. Each gets a stable ID (C-YYYY-MM-DD-NNN).

_(none yet)_
`,
  reflections: `# Reflections

Periodic synthesis across the corpus. **Newest on top.** Each reflection reviews recent
additions and updates the semantic layer (themes, questions, gaps, contradictions).

---

_(no reflections yet)_
`,
};

function seedMemoryDashboard() {
  const papers = cfg.internal_artifacts?.papers ?? [];
  const tracked = papers.length ? papers.join(', ') : '_(none yet)_';
  return `# Corpus Memory — Dashboard

This is the entry point to your **corpus memory** (Layer 3): a two-layer episodic + semantic memory over your literature and projects. Distinct from cross-session auto-memory (Layer 2) — see \`CLAUDE_REFERENCE.md\` → Memory Architecture.

Query it with the \`/research-memory\` skill (\`recall\`, \`status\`, \`log\`, \`inspect\`), or just \`grep\` the files.

## Layout

- \`episodic/_external/_by-citekey/\` — one note per literature source (findings, themes, links to your papers)
- \`episodic/_internal/{papers,country,special}/\` — rolling state per research artifact (the source of truth for a paper's themes and linked sources)
- \`semantic/{themes,questions,gaps,contradictions}/\` — distilled cross-corpus synthesis
- \`reflections/REFLECTIONS.md\` — periodic synthesis, newest on top

## Current state

- **Papers tracked:** ${tracked}
- **External sources:** 0 (add via \`/research-memory\` or the future Zotero-ingestion module)
- **Open questions / gaps / contradictions:** see \`semantic/\`

_Update this dashboard as the corpus grows._
`;
}

function seedInternalIndex() {
  const tierMap = artifactToTier();
  const papersDir = cfg.paths.episodic_internal_papers;
  const countryDir = cfg.paths.episodic_internal_country;
  const rows = [];
  const add = (id, type, dirRel) => {
    const file = resolvePath(path.join(dirRel, `${id}.md`));
    const phase = fmValue(file, 'phase') ?? '1';
    const status = fmValue(file, 'status') ?? 'scoping';
    const synced = fmValue(file, 'last_synced');
    const syncedCell = synced && synced !== 'null' ? synced : '—';
    rows.push(`| ${id} | ${type} | ${phase} | ${status} | ${syncedCell} |`);
  };
  for (const id of cfg.internal_artifacts?.papers ?? []) add(id, 'paper', papersDir);
  for (const id of cfg.internal_artifacts?.country ?? []) add(id, 'country', countryDir);
  if (!rows.length) rows.push('| _(none yet)_ | | | | |');
  return `# Internal Artifacts Index

Rolling state, one file per research artifact (paper / country / special project).

| Artifact | Type | Phase | Status | Last synced |
|----------|------|-------|--------|-------------|
${rows.join('\n')}
`;
}

function rollingTemplate(id, type, tier) {
  return `---
internal_id: ${id}
artifact_type: ${type}
phase: 1
tier: ${tier}
status: scoping
last_synced: null
themes: []
linked_external: []
---

# ${id} — rolling state

The structured, index-friendly companion to \`papers/${id}/NOTES.md\`. This file is the **single source of truth** for this ${type}'s themes, linked sources, and status narrative in the corpus layer.

## Summary

_One paragraph on where this ${type} stands analytically._

## Themes

_Cross-corpus themes this ${type} touches (link to \`semantic/themes/\`)._

## Linked sources

_Citekeys from \`episodic/_external/\` that matter to this ${type}, with a note on why._

${cfg.manual_notes_marker || '## Manual notes'}

_Free-form notes. The \`${cfg.manual_notes_marker || '## Manual notes'}\` marker preserves this section across automated syncs._
`;
}

// --- 1. directories ---------------------------------------------------------

const dirKeys = [
  'episodic_external',
  'episodic_internal_papers',
  'episodic_internal_country',
  'episodic_internal_special',
  'logs',
];
for (const k of dirKeys) if (cfg.paths[k]) ensureDir(cfg.paths[k]);

// .gitkeep for dirs that can legitimately stay empty
for (const k of ['episodic_external', 'episodic_internal_country', 'episodic_internal_special', 'logs']) {
  if (cfg.paths[k]) ensureGitkeep(cfg.paths[k]);
}

// --- 2. seeded index / dashboard files --------------------------------------

ensureFile('research_memory/MEMORY.md', seedMemoryDashboard());
ensureFile('research_memory/episodic/_external/INDEX.md', SEED.externalIndex);
ensureFile('research_memory/episodic/_internal/INDEX.md', seedInternalIndex());

if (cfg.paths.semantic_themes_index) ensureFile(cfg.paths.semantic_themes_index, SEED.themesIndex);
if (cfg.paths.semantic_questions_open) ensureFile(cfg.paths.semantic_questions_open, SEED.open);
if (cfg.paths.semantic_questions_answered) ensureFile(cfg.paths.semantic_questions_answered, SEED.answered);
if (cfg.paths.semantic_gaps) ensureFile(cfg.paths.semantic_gaps, SEED.gaps);
if (cfg.paths.semantic_contradictions) ensureFile(cfg.paths.semantic_contradictions, SEED.contradictions);
if (cfg.paths.reflections) ensureFile(cfg.paths.reflections, SEED.reflections);

// --- 3. rolling-state files for configured artifacts ------------------------

const tierMap = artifactToTier();
for (const id of cfg.internal_artifacts?.papers ?? []) {
  ensureFile(path.join(cfg.paths.episodic_internal_papers, `${id}.md`), rollingTemplate(id, 'paper', tierMap[id] ?? '2'));
}
for (const id of cfg.internal_artifacts?.country ?? []) {
  ensureFile(path.join(cfg.paths.episodic_internal_country, `${id}.md`), rollingTemplate(id, 'country', tierMap[id] ?? '2'));
}

// --- summary ----------------------------------------------------------------

if (created.length === 0) {
  log('research-memory bootstrap — tree already complete, nothing to create.');
} else {
  log(`research-memory bootstrap — created ${created.length} item(s):`);
  for (const c of created) log(`  + ${c}`);
}
