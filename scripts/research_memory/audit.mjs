#!/usr/bin/env node
/**
 * research-memory audit — read-only health / completeness check.
 *
 * Verifies the corpus-memory tree against `research_memory/config.json` and
 * emits findings by severity:
 *   [CRITICAL] — the tree is structurally broken (missing core directory)
 *   [HIGH]     — a defect that breaks discoverability or linking
 *   [MED]      — partial completeness; worth fixing, not a blocker
 *   [LOW]      — cosmetic
 *
 * Exit code: 1 if any CRITICAL finding, 0 otherwise. Writes a JSON log to
 * research_memory/_logs/audit_{YYYY-MM-DD}.json. Fully offline — no MCP, no
 * network, no reference-manager dependency.
 *
 * Usage:
 *   node scripts/research_memory/audit.mjs            # text report + JSON log
 *   node scripts/research_memory/audit.mjs --quiet     # JSON log only (for cron)
 */

import fs from 'node:fs';
import path from 'node:path';
import { loadConfig, resolvePath, researchMemoryEnabled, PROJECT_ROOT } from './config.mjs';

const args = process.argv.slice(2);
const QUIET = args.includes('--quiet');

function log(msg) {
  if (!QUIET) console.log(msg);
}

if (!researchMemoryEnabled()) {
  log('research_memory tier is disabled (tiers.research_memory: false). Nothing to audit.');
  process.exit(0);
}

const cfg = loadConfig();
const findings = [];
function flag(severity, code, message, evidence = null) {
  findings.push({ severity, code, message, evidence });
}

// --- frontmatter helpers (no YAML dependency) -------------------------------

function readFrontmatter(filepath) {
  const txt = fs.readFileSync(filepath, 'utf8');
  if (!txt.startsWith('---\n')) return null;
  const end = txt.indexOf('\n---\n', 4);
  if (end === -1) return null;
  return txt.slice(4, end);
}

function fmHas(fm, field) {
  const re = new RegExp('^' + field.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*:', 'm');
  return re.test(fm);
}

const WIKILINK_TOKEN = /\[\[([^\]]+)\]\]/g;

// --- resolve the pieces of the tree from config -----------------------------

const BY_CITEKEY = resolvePath(cfg.paths.episodic_external);
const PAPERS_DIR = resolvePath(cfg.paths.episodic_internal_papers);
const COUNTRY_DIR = resolvePath(cfg.paths.episodic_internal_country);
const LOG_DIR = resolvePath(cfg.paths.logs);
const MARKER = cfg.manual_notes_marker || '## Manual notes';

// --- check (a): structural completeness -------------------------------------

const EXTRA_INDEX_FILES = [
  'research_memory/MEMORY.md',
  'research_memory/episodic/_external/INDEX.md',
  'research_memory/episodic/_internal/INDEX.md',
];

{
  for (const [key, rel] of Object.entries(cfg.paths)) {
    const abs = resolvePath(rel);
    const isFile = rel.endsWith('.md');
    if (!fs.existsSync(abs)) {
      if (isFile) {
        flag('MED', 'missing_index_file', `Expected index file missing: ${rel}`, { key });
      } else {
        flag('HIGH', 'missing_directory', `Expected directory missing: ${rel}`, { key });
      }
    }
  }
  for (const rel of EXTRA_INDEX_FILES) {
    if (!fs.existsSync(resolvePath(rel))) {
      flag('MED', 'missing_index_file', `Expected index file missing: ${rel}`);
    }
  }
  // A missing episodic_external directory means the corpus root is gone.
  if (!fs.existsSync(BY_CITEKEY)) {
    flag('CRITICAL', 'no_corpus_root', `Episodic external directory absent — run: npm run memory:bootstrap`, {
      path: cfg.paths.episodic_external,
    });
  }
}

// --- external notes: gather citekeys, validate frontmatter ------------------

const externalFiles = fs.existsSync(BY_CITEKEY)
  ? fs.readdirSync(BY_CITEKEY).filter((f) => f.endsWith('.md'))
  : [];
const citekeys = new Set(externalFiles.map((f) => f.replace(/\.md$/, '')));

// --- check (b): external note frontmatter -----------------------------------

for (const f of externalFiles) {
  const fm = readFrontmatter(path.join(BY_CITEKEY, f));
  if (!fm) {
    flag('HIGH', 'no_frontmatter', `External note has no parseable frontmatter`, { file: f });
    continue;
  }
  if (!fmHas(fm, 'citekey')) {
    flag('MED', 'external_missing_citekey', `External note missing 'citekey' field`, { file: f });
  }
}

// --- check (c): internal rolling files --------------------------------------

function auditInternal(id, type, dir) {
  const file = path.join(dir, `${id}.md`);
  if (!fs.existsSync(file)) {
    flag('HIGH', 'missing_rolling_file', `No rolling-state file for ${type} '${id}' — run: npm run memory:bootstrap`, {
      expected: path.relative(PROJECT_ROOT, file),
    });
    return;
  }
  const fm = readFrontmatter(file);
  if (!fm) {
    flag('HIGH', 'internal_no_frontmatter', `Rolling file for '${id}' has no parseable frontmatter`, { file: path.relative(PROJECT_ROOT, file) });
    return;
  }
  for (const field of ['internal_id', 'artifact_type', 'status']) {
    if (!fmHas(fm, field)) {
      flag('MED', 'internal_missing_field', `Rolling file for '${id}' missing '${field}'`, { file: path.relative(PROJECT_ROOT, file) });
    }
  }
  const body = fs.readFileSync(file, 'utf8');
  if (!body.includes(MARKER)) {
    flag('MED', 'missing_notes_marker', `Rolling file for '${id}' has no '${MARKER}' marker (manual notes not preserved across syncs)`, {
      file: path.relative(PROJECT_ROOT, file),
    });
  }
}

for (const id of cfg.internal_artifacts?.papers ?? []) auditInternal(id, 'paper', PAPERS_DIR);
for (const id of cfg.internal_artifacts?.country ?? []) auditInternal(id, 'country', COUNTRY_DIR);

// --- check (d): wikilink validity across external notes ---------------------

{
  const orphans = new Map();
  for (const f of externalFiles) {
    const txt = fs.readFileSync(path.join(BY_CITEKEY, f), 'utf8');
    const body = txt.split(/\n---\n/).slice(1).join('\n---\n');
    let m;
    while ((m = WIKILINK_TOKEN.exec(body)) !== null) {
      const target = m[1].trim();
      // A wikilink to another source note must resolve to an existing citekey.
      // Links to themes/questions (non-citekey text) are left alone.
      if (citekeys.size && !citekeys.has(target) && /^[a-z]/.test(target) && !target.includes(' ')) {
        if (!orphans.has(target)) orphans.set(target, []);
        orphans.get(target).push(f);
      }
    }
  }
  if (orphans.size) {
    const examples = [...orphans.entries()].slice(0, 10).map(([t, refs]) => ({ target: t, referenced_by: refs[0] }));
    flag('MED', 'orphan_wikilinks', `${orphans.size} wikilink target(s) do not resolve to an existing source note`, { examples });
  }
}

// --- check (e): external index drift ----------------------------------------

{
  const indexPath = resolvePath('research_memory/episodic/_external/INDEX.md');
  if (fs.existsSync(indexPath) && externalFiles.length) {
    const indexTxt = fs.readFileSync(indexPath, 'utf8');
    const notIndexed = [...citekeys].filter((ck) => !indexTxt.includes(ck));
    if (notIndexed.length) {
      flag('MED', 'index_drift', `${notIndexed.length} source note(s) not listed in _external/INDEX.md`, {
        examples: notIndexed.slice(0, 10),
      });
    }
  }
}

// --- output -----------------------------------------------------------------

const counts = {
  CRITICAL: findings.filter((f) => f.severity === 'CRITICAL').length,
  HIGH: findings.filter((f) => f.severity === 'HIGH').length,
  MED: findings.filter((f) => f.severity === 'MED').length,
  LOW: findings.filter((f) => f.severity === 'LOW').length,
};

const date = new Date().toISOString().slice(0, 10);
const summary = {
  timestamp: new Date().toISOString(),
  external_notes_audited: externalFiles.length,
  internal_artifacts_audited:
    (cfg.internal_artifacts?.papers?.length ?? 0) + (cfg.internal_artifacts?.country?.length ?? 0),
  counts,
  findings,
};

if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR, { recursive: true });
const logPath = path.join(LOG_DIR, `audit_${date}.json`);
fs.writeFileSync(logPath, JSON.stringify(summary, null, 2) + '\n');

if (!QUIET) {
  console.log(`research-memory audit — ${externalFiles.length} external note(s), ${summary.internal_artifacts_audited} internal artifact(s)`);
  console.log(`  CRITICAL: ${counts.CRITICAL}    HIGH: ${counts.HIGH}    MED: ${counts.MED}    LOW: ${counts.LOW}`);
  for (const f of findings) {
    console.log(`\n[${f.severity}] ${f.code}: ${f.message}`);
    if (f.evidence?.examples) {
      for (const e of f.evidence.examples.slice(0, 5)) {
        console.log(`    - ${typeof e === 'string' ? e : JSON.stringify(e)}`);
      }
    }
  }
  if (!findings.length) console.log('\n  Clean — no findings.');
  console.log(`\nFull log: ${path.relative(PROJECT_ROOT, logPath)}`);
}

process.exit(counts.CRITICAL > 0 ? 1 : 0);
