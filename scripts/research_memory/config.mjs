/**
 * Shared configuration loader for the corpus-memory scripts.
 *
 * Single source of truth: `research_memory/config.json`. Both bootstrap.mjs and
 * audit.mjs read from here so paths never drift between subcommands. Zero
 * runtime dependencies — Node built-ins only.
 *
 * (Ported from the DRF source system's loader; the Zotero-tag helpers were
 * dropped — the kit's automated-ingestion module is not shipped in v1.)
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
export const CONFIG_PATH = path.join(PROJECT_ROOT, 'research_memory', 'config.json');

let _cached = null;

export function loadConfig() {
  if (_cached) return _cached;
  if (!fs.existsSync(CONFIG_PATH)) {
    throw new Error(`research_memory/config.json not found at ${CONFIG_PATH}`);
  }
  _cached = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
  return _cached;
}

/** Resolve a project-relative path (as stored in config.json) to absolute. */
export function resolvePath(relPath) {
  return path.join(PROJECT_ROOT, relPath);
}

/** Inverse of config.tiers: artifact_id -> tier ("1" | "2" | "3"). */
export function artifactToTier() {
  const cfg = loadConfig();
  const map = {};
  for (const [tier, ids] of Object.entries(cfg.tiers || {})) {
    for (const id of ids) map[id] = tier;
  }
  return map;
}

/**
 * Is the corpus-memory tier enabled? Reads research-config.yml with a small
 * regex (no YAML dependency). Returns true when the flag is absent or the file
 * is missing, so an explicit `npm run memory:*` invocation is never silently
 * blocked — only an explicit `research_memory: false` disables.
 */
export function researchMemoryEnabled() {
  const cfgPath = path.join(PROJECT_ROOT, 'research-config.yml');
  if (!fs.existsSync(cfgPath)) return true;
  const txt = fs.readFileSync(cfgPath, 'utf8');
  const m = txt.match(/^\s*research_memory:\s*(true|false)\b/im);
  return m ? m[1].toLowerCase() === 'true' : true;
}
