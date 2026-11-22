#!/usr/bin/env node
/**
 * build-queue.mjs — the deterministic step between the librarian agents and the approval queue.
 *
 *   node scripts/zotero/build-queue.mjs --date YYYY-MM-DD [--dir outputs/librarian] [--out <file>] [--force]
 *
 * Reads every `*_<date>.proposals.json` in --dir, validates each action, drops duplicates (first wins),
 * assigns ids from 1, sets every status to `pending`, records `source_agent`, and writes
 * `approval_queue_<date>.json` atomically. Rejected proposals go to `rejected_<date>.json` with reasons.
 * No network. Exit 0 on success (even with rejections), 1 on argument/file errors or no proposals.
 */
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { normaliseDoi } from './_lib/crossref-item.mjs';
import { isPlaceholder, fixPairsOf, saveQueue } from './approval-queue.mjs';

class UsageError extends Error {}

const KNOWN_TYPES = new Set(['add_item', 'fix_metadata', 'add_tag', 'add_to_collection']);
const nonEmpty = (v) => typeof v === 'string' && v.trim() !== '' && !isPlaceholder(v);

/** Returns { action } with a cleaned copy, or { reason }. */
export function validateAction(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return { reason: 'action is not an object' };
  const { type } = raw;
  if (!KNOWN_TYPES.has(type)) return { reason: `unknown or unsupported type "${type}"` };
  if (!nonEmpty(raw.title)) return { reason: 'missing or placeholder title' };
  const d = raw.details;
  if (!d || typeof d !== 'object' || Array.isArray(d)) return { reason: 'missing details object' };
  const details = { ...d };

  if (type === 'add_item') {
    const doi = normaliseDoi(d.doi || d.DOI);
    const hasTitle = nonEmpty(d.title);
    if (!doi && !hasTitle) return { reason: 'add_item needs a title or a DOI' };
    if (d.title !== undefined && !hasTitle) return { reason: 'placeholder value in details.title' };
    if (doi) details.doi = doi;
    delete details.DOI;
    for (const k of ['venue', 'date', 'abstract', 'url']) {
      if (details[k] !== undefined && isPlaceholder(details[k])) return { reason: `placeholder value in details.${k}` };
    }
    if (details.relevance !== undefined && !['high', 'medium', 'low'].includes(details.relevance)) {
      return { reason: 'details.relevance must be high, medium or low' };
    }
  } else if (type === 'fix_metadata') {
    if (!nonEmpty(d.item_key)) return { reason: 'fix_metadata needs details.item_key' };
    const pairs = fixPairsOf(d);
    if (!pairs.length) return { reason: 'fix_metadata needs at least one change' };
    const bad = pairs.filter(([, v]) => isPlaceholder(v)).map(([f]) => f);
    if (bad.length) return { reason: `placeholder value for: ${bad.join(', ')}` };
    if (d.doi !== undefined || d.proposed_changes?.doi !== undefined) {
      const norm = normaliseDoi(d.proposed_changes?.doi ?? d.doi);
      if (!norm) return { reason: 'invalid DOI in proposed change' };
      if (details.proposed_changes?.doi !== undefined) details.proposed_changes = { ...details.proposed_changes, doi: norm };
    }
  } else if (type === 'add_tag') {
    if (!nonEmpty(d.item_key)) return { reason: 'add_tag needs details.item_key' };
    if (!Array.isArray(d.tags) || !d.tags.length || !d.tags.every(nonEmpty)) return { reason: 'add_tag needs details.tags: a non-empty array of real strings' };
    details.tags = d.tags.map((t) => t.trim());
  } else if (type === 'add_to_collection') {
    if (!nonEmpty(d.item_key)) return { reason: 'add_to_collection needs details.item_key' };
    if (!nonEmpty(d.collection_key)) return { reason: 'add_to_collection needs details.collection_key' };
  }

  const action = { type, title: raw.title.trim() };
  if (raw.paper !== undefined) {
    if (!nonEmpty(raw.paper)) return { reason: 'placeholder value in paper' };
    action.paper = raw.paper;
  }
  action.details = details;
  return { action };
}

/** Keys that make two actions the same proposal. add_tag may yield several (one per tag). */
export function dedupeKeys(a) {
  const d = a.details;
  if (a.type === 'add_item') {
    const doi = normaliseDoi(d.doi);
    return doi ? [`add_item|${doi}`] : [`add_item|title|${String(d.title).toLowerCase().replace(/\s+/g, ' ').trim()}`];
  }
  if (a.type === 'fix_metadata') return fixPairsOf(d).map(([f]) => `fix|${d.item_key}|${f.toLowerCase()}`);
  if (a.type === 'add_tag') return d.tags.map((t) => `tag|${d.item_key}|${t.toLowerCase()}`);
  return [`coll|${d.item_key}|${d.collection_key}`];
}

function parseArgs(argv) {
  const o = { dir: 'outputs/librarian', force: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--force') o.force = true;
    else if (['--date', '--dir', '--out'].includes(a)) {
      if (argv[i + 1] === undefined || argv[i + 1].startsWith('--')) throw new UsageError(`${a} needs a value`);
      o[a.slice(2)] = argv[++i];
    } else throw new UsageError(`Unknown argument: ${a}`);
  }
  if (!o.date) throw new UsageError('--date YYYY-MM-DD is required');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(o.date)) throw new UsageError(`--date must be YYYY-MM-DD, got "${o.date}"`);
  return o;
}

export function main(argv) {
  const o = parseArgs(argv);
  const dir = path.resolve(o.dir);
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) throw new UsageError(`Directory not found: ${o.dir}`);
  const suffix = `_${o.date}.proposals.json`;
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(suffix)).sort();
  if (!files.length) throw new UsageError(`No proposals file for ${o.date} in ${o.dir} (expected *${suffix}). Run the librarian agents first.`);

  const out = path.resolve(o.out || path.join(dir, `approval_queue_${o.date}.json`));
  if (fs.existsSync(out)) {
    if (!o.force) throw new UsageError(`Queue already exists: ${out}. Use --force to rebuild (refused if any action has been decided).`);
    let existing;
    try { existing = JSON.parse(fs.readFileSync(out, 'utf8')); } catch (err) { throw new UsageError(`Existing queue is unreadable (${err.message}); not overwriting. Move it aside first.`); }
    const decided = (existing.actions || []).filter((a) => a.status !== 'pending');
    if (decided.length) throw new UsageError(`Refusing --force: ${decided.length} action(s) in the existing queue are no longer pending (${[...new Set(decided.map((a) => a.status))].join(', ')}). Decisions must not be lost.`);
  }

  const accepted = [];
  const rejected = [];
  const dupes = [];
  const seen = new Set();
  const fileErrors = [];
  const agents = [];

  for (const f of files) {
    let data;
    try { data = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')); } catch (err) { fileErrors.push(`${f}: invalid JSON (${err.message})`); continue; }
    if (!data || !Array.isArray(data.actions)) { fileErrors.push(`${f}: no "actions" array`); continue; }
    const agent = typeof data.agent === 'string' && data.agent ? data.agent : f.slice(0, -suffix.length);
    agents.push(agent);
    data.actions.forEach((raw, idx) => {
      const { action, reason } = validateAction(raw);
      if (!action) { rejected.push({ source_file: f, source_agent: agent, index: idx, reason, proposal: raw }); return; }
      const keys = dedupeKeys(action);
      if (keys.every((k) => seen.has(k))) { dupes.push({ source_file: f, source_agent: agent, index: idx, keys, proposal: raw }); return; }
      keys.forEach((k) => seen.add(k));
      accepted.push({ ...action, source_agent: agent });
    });
  }

  const actions = accepted.map((a, i) => {
    const { type, title, paper, details, source_agent } = a;
    return { id: i + 1, type, status: 'pending', title, ...(paper !== undefined ? { paper } : {}), details, source_agent };
  });
  const queue = { date: o.date, source: `librarian-team: ${agents.join(', ') || 'none'}`, actions };
  const rejectedPath = path.join(path.dirname(out), `rejected_${o.date}.json`);
  const rejectedBody = { date: o.date, rejected, duplicates_dropped: dupes, file_errors: fileErrors };

  if (fileErrors.length && !actions.length && !rejected.length) {
    // Every file was unreadable: nothing to build.
    for (const e of fileErrors) console.error(`ERROR ${e}`);
    throw new UsageError('No readable proposals file.');
  }
  fs.mkdirSync(path.dirname(out), { recursive: true });
  saveQueue(out, queue);
  saveQueue(rejectedPath, rejectedBody);

  console.log(`Queue written: ${out}`);
  console.log(`  accepted: ${actions.length}   rejected: ${rejected.length}   duplicates dropped: ${dupes.length}`);
  for (const r of rejected) console.log(`  rejected  ${r.source_file} #${r.index}: ${r.reason}`);
  for (const d of dupes) console.log(`  duplicate ${d.source_file} #${d.index}: ${d.keys.join(', ')}`);
  for (const e of fileErrors) console.log(`  FILE ERROR ${e}`);
  if (rejected.length || dupes.length || fileErrors.length) console.log(`Details: ${rejectedPath}`);
  return 0;
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(fs.realpathSync(process.argv[1])).href;
if (isMain) {
  try {
    process.exit(main(process.argv.slice(2)));
  } catch (err) {
    console.error(err instanceof UsageError ? `Error: ${err.message}` : `Error: ${err.stack || err}`);
    process.exit(1);
  }
}
